DELIMITER $$

CREATE TRIGGER trg_region_demand_before_insert
BEFORE INSERT ON REGION_DETAILS
FOR EACH ROW
BEGIN
    -- Check if the incoming Demand_MU value is not NULL
    -- This value is assumed to be in MW
    IF NEW.Demand_MU IS NOT NULL THEN
        
        -- Convert the value from MW to Million Units (MU)
        -- (MW * 24 hours) / 1000 MWh/MU
        SET NEW.Demand_MU = NEW.Demand_MU * 0.024;
        
        -- IF NEW.Demand_MU > 100 THEN
        --    SET NEW.Demand_MU = NEW.Demand_MU - 15;
        -- END IF;
        
    END IF;
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_UpdateRegionGenerationFromProduction()
BEGIN
    -- This query joins REGION_DETAILS with an aggregated subquery
    -- that calculates the total generation (sum of Todays_Actual_MU)
    -- for each state and date from the PRODUCTIONLOG.
    
    UPDATE REGION_DETAILS AS rd
    JOIN (
        -- Subquery: Calculate the total actual generation for each state and date
        SELECT 
            p.State_Code,
            pl.Log_Date,
            SUM(pl.Todays_Actual_MU) AS Total_Actual_MU
        FROM 
            PRODUCTIONLOG AS pl
        JOIN 
            POWERPLANTS AS p ON pl.Plant_ID = p.Plant_ID
        WHERE
            p.State_Code IS NOT NULL
        GROUP BY 
            p.State_Code, pl.Log_Date
    ) AS daily_totals 
    ON 
        rd.State_Code = daily_totals.State_Code 
        AND rd.Report_Date = daily_totals.Log_Date

    -- Set the Generated_MU column to the calculated total
    SET 
        rd.Generated_MU = daily_totals.Total_Actual_MU;
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_UpdateRegionSurplusAndImports()
BEGIN
    UPDATE REGION_DETAILS
    SET 
        Surplus_MU = CASE 
                         WHEN Generated_MU > Demand_MU THEN (Generated_MU - Demand_MU) 
                         ELSE 0 
                     END,
        
        Imported_MU = CASE 
                          WHEN Demand_MU > Generated_MU THEN (Demand_MU - Generated_MU) 
                          ELSE 0 
                      END
    WHERE 
        Generated_MU IS NOT NULL 
        AND Demand_MU IS NOT NULL;

END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_CalculatePlantEfficiency()
BEGIN
    UPDATE PRODUCTIONLOG
    SET 
        -- Calculating efficiency
        Efficiency_Percentage = (Todays_Actual_MU / Capable_Generation_MU) * 100
    WHERE 
        -- Preventing division by zero errors
        Capable_Generation_MU IS NOT NULL 
        AND Capable_Generation_MU > 0
        AND Todays_Actual_MU IS NOT NULL;
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_InsertAllMissingActiveStatuses()
BEGIN
    -- Insert 'Active' status records for plant/date combinations
    -- that have NO entries at all in OPERATIONAL_STATUS.
    
    INSERT INTO OPERATIONAL_STATUS (
        Plant_ID, 
        Unit_Number, 
        Status_Date, 
        Status, 
        Cap_Under_Outage_MW, 
        Expected_Sync_Date, 
        Remarks, 
        Outage_Date
    )
    -- Select all (Plant, Date) combinations...
    SELECT 
        p.Plant_ID,
        'Main' AS Unit_Number,     
        d.`Date` AS Status_Date,   
        'Active' AS Status,        
        0.00 AS Cap_Under_Outage_MW, 
        NULL AS Expected_Sync_Date,  
        NULL AS Remarks,             
        NULL AS Outage_Date          
    FROM 
        POWERPLANTS p
    CROSS JOIN 
        DATE_DIM d
    WHERE 
        -- ...for which NOT A SINGLE record exists in OPERATIONAL_STATUS
        -- for that Plant_ID and Date (regardless of Unit_Number)
        NOT EXISTS (
            SELECT 1 
            FROM OPERATIONAL_STATUS os
            WHERE os.Plant_ID = p.Plant_ID 
              AND os.Status_Date = d.`Date`
        );
END$$

DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_GenerateDailyEnergyReport(IN report_date DATE)
BEGIN
-- Safe aggregation: read totals directly from REGION_DETAILS (one row per state/date)
-- This avoids row-multiplication caused by joining POWERPLANTS/PRODUCTIONLOG
-- before aggregation.
SELECT
rd.State_Code,
rd.Report_Date,
COALESCE(rd.Generated_MU, 0) AS total_generated_mu,
COALESCE(rd.Demand_MU, 0) AS total_demand_mu,
COALESCE(rd.Surplus_MU, 0) AS total_surplus_mu,
COALESCE(rd.Imported_MU, 0) AS total_imported_mu
FROM REGION_DETAILS rd
WHERE rd.Report_Date = report_date
ORDER BY rd.State_Code;
END$$
DELIMITER ;

-- 2) Stored procedure: sp_IdentifyUnderperformingPlants
DELIMITER $$
CREATE PROCEDURE sp_IdentifyUnderperformingPlants(IN threshold_efficiency DECIMAL(5,2), IN days_to_check INT)
BEGIN
    SELECT
        p.Plant_ID,
        p.Plant_Name,
        s.State_Name,
        ROUND(AVG(pl.Efficiency_Percentage), 2) AS avg_efficiency
    FROM POWERPLANTS p
    LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
    LEFT JOIN STATE s ON p.State_Code = s.State_Code
    WHERE pl.Log_Date >= DATE_SUB(CURDATE(), INTERVAL days_to_check DAY)
    GROUP BY p.Plant_ID, p.Plant_Name, s.State_Name
    HAVING AVG(pl.Efficiency_Percentage) < threshold_efficiency
    ORDER BY avg_efficiency ASC;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_CalculateRegionalMetrics(IN start_date DATE, IN end_date DATE)
BEGIN
    -- Aggregate production data by state first
    WITH StateProduction AS (
        SELECT 
            p.State_Code,
            COUNT(DISTINCT p.Plant_ID) AS Total_Plants,
            COALESCE(SUM(pl.Todays_Actual_MU), 0) AS Total_Generated_MU
        FROM POWERPLANTS p
        LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID 
            AND pl.Log_Date BETWEEN start_date AND end_date
        GROUP BY p.State_Code
    ),
    -- Aggregate region details by state separately
    StateDemand AS (
        SELECT 
            State_Code,
            COALESCE(SUM(Demand_MU), 0) AS Total_Demand_MU
        FROM REGION_DETAILS
        WHERE Report_Date BETWEEN start_date AND end_date
        GROUP BY State_Code
    )
    -- Now joining the pre-aggregated results
    SELECT
        s.Region,
        COALESCE(SUM(sp.Total_Plants), 0) AS Total_Plants,
        COALESCE(SUM(sp.Total_Generated_MU), 0) AS Total_Generated_MU,
        COALESCE(SUM(sd.Total_Demand_MU), 0) AS Total_Demand_MU,
        CASE 
            WHEN SUM(sd.Total_Demand_MU) > 0 THEN
                ROUND((SUM(sp.Total_Generated_MU) / SUM(sd.Total_Demand_MU)) * 100, 2)
            ELSE 0
        END AS Supply_Percentage
    FROM STATE s
    LEFT JOIN StateProduction sp ON s.State_Code = sp.State_Code
    LEFT JOIN StateDemand sd ON s.State_Code = sd.State_Code
    GROUP BY s.Region
    ORDER BY Total_Generated_MU DESC;
END$$
DELIMITER ;

-- ===========================
-- MySQL FUNCTIONS
-- ===========================

-- Function 1: Calculate Renewable Percentage
DELIMITER $$
CREATE FUNCTION fn_calculate_renewable_percentage(
    renewable_mu DECIMAL(15,2),
    total_mu DECIMAL(15,2)
)
RETURNS DECIMAL(5,2)
DETERMINISTIC
BEGIN
    RETURN ROUND((renewable_mu / NULLIF(total_mu, 0)) * 100, 2);
END$$
DELIMITER ;

-- Function 2: Classify Energy Category
DELIMITER $$
CREATE FUNCTION fn_energy_category(energy_type VARCHAR(50))
RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    IF energy_type IN ('HYDRO', 'WIND', 'SOLAR', 'BIOMASS') THEN
        RETURN 'Renewable';
    ELSE
        RETURN 'Non-Renewable';
    END IF;
END$$
DELIMITER ;

-- Function 3: Determine Coal Stock Alert Severity
DELIMITER $$
CREATE FUNCTION fn_coal_stock_severity(coal_days INT)
RETURNS VARCHAR(10)
DETERMINISTIC
BEGIN
    IF coal_days < 4 THEN 
        RETURN 'CRITICAL';
    ELSEIF coal_days < 7 THEN 
        RETURN 'WARNING';
    ELSE 
        RETURN 'NORMAL';
    END IF;
END$$
DELIMITER ;
