CREATE DATABASE IF NOT EXISTS IndianEnergyDB;
USE IndianEnergyDB;

-- STATE Entity
CREATE TABLE STATE (
    State_Code VARCHAR(10) PRIMARY KEY,
    State_Name VARCHAR(100),
    Region VARCHAR(100),
    Population BIGINT
);


-- SECTOR Entity
CREATE TABLE SECTOR (
    Sector_ID VARCHAR(10) PRIMARY KEY,
    Sector_Name VARCHAR(100) NOT NULL -- e.g., 'State', 'Private', 'Central'
);

-- ENERGYTYPE Entity 
CREATE TABLE ENERGYTYPE (
    Type_ID VARCHAR(10) PRIMARY KEY,
    Type_Name VARCHAR(100),
    Description TEXT
);

-- DATE_DIM Entity 
CREATE TABLE DATE_DIM (
    `Date` DATE PRIMARY KEY,
    Day INT,
    Month INT,
    Year INT
);

CREATE TABLE POWERPLANTS (
    Plant_ID VARCHAR(20) PRIMARY KEY,
    Plant_Name VARCHAR(255) NOT NULL,
    State_Code VARCHAR(10),
    Sector_ID VARCHAR(10),
    Type_ID VARCHAR(10),
        
    FOREIGN KEY (State_Code) REFERENCES STATE(State_Code),
    FOREIGN KEY (Sector_ID) REFERENCES SECTOR(Sector_ID),
    FOREIGN KEY (Type_ID) REFERENCES ENERGYTYPE(Type_ID)
);

-- OPERATIONAL_STATUS Entity (Weak entity, depends on POWERPLANTS and DATE_DIM)
CREATE TABLE OPERATIONAL_STATUS (
    Plant_ID VARCHAR(20),
    Unit_Number VARCHAR(20),
    Status_Date DATE, 
    Cap_Under_Outage_MW DECIMAL(10, 2),
    Status ENUM('Active', 'Under Outage', 'Not Commisioned'), 
    Outage_Date DATE,
    Expected_Sync_Date DATE, 
    Remarks TEXT,
    
    PRIMARY KEY (Plant_ID, Unit_Number, Status_Date),
    
    FOREIGN KEY (Plant_ID) REFERENCES POWERPLANTS(Plant_ID),
    FOREIGN KEY (Status_Date) REFERENCES DATE_DIM(`Date`)
);

-- REGION_DETAILS Entity (Fact table linking STATE and DATE_DIM)
CREATE TABLE REGION_DETAILS (
    State_Code VARCHAR(10),
    Report_Date DATE, 
    Generated_MU DECIMAL(12, 2),
    Imported_MU DECIMAL(12, 2),
    Surplus_MU DECIMAL(12, 2),
    Demand_MU DECIMAL(12, 2),
    Monitored_Capacity_MW DECIMAL(10, 2),
    Grid_Frequency_HZ DECIMAL(5, 2), 
    
    PRIMARY KEY (State_Code, Report_Date),
    FOREIGN KEY (State_Code) REFERENCES STATE(State_Code),
    FOREIGN KEY (Report_Date) REFERENCES DATE_DIM(`Date`)
);

-- PRODUCTIONLOG Entity (Fact table linking POWERPLANTS and DATE_DIM)
CREATE TABLE PRODUCTIONLOG (
    Plant_ID VARCHAR(20),
    Log_Date DATE, 
    Efficiency_Percentage DECIMAL(6, 2),
    Todays_Actual_MU DECIMAL(12, 2),
    Capable_Generation_MU DECIMAL(12, 2),
    Operational_Capacity_MW DECIMAL(10, 2),
    Coal_Stock_Days DECIMAL(10, 2), 
    
    PRIMARY KEY (Plant_ID, Log_Date),
    FOREIGN KEY (Plant_ID) REFERENCES POWERPLANTS(Plant_ID),
    FOREIGN KEY (Log_Date) REFERENCES DATE_DIM(`Date`)
);

INSERT INTO STATE (State_Code, State_Name, Region, Population)
VALUES 
-- Northern Region
('DL', 'Delhi', 'Northern', NULL),
('HRN', 'Haryana', 'Northern', NULL),
('HP', 'Himachal Pradesh', 'Northern', NULL),
('JAK', 'Jammu and Kashmir', 'Northern', NULL),
('LDK', 'Ladakh', 'Northern', NULL),
('PNB', 'Punjab', 'Northern', NULL),
('RJ', 'Rajasthan', 'Northern', NULL),
('UTK', 'Uttarakhand', 'Northern', NULL),
('UP', 'Uttar Pradesh', 'Northern', NULL),

-- North Eastern Region
('ACP', 'Arunachal Pradesh', 'North Eastern', NULL),
('ASM', 'Assam', 'North Eastern', NULL),
('MIP', 'Manipur', 'North Eastern', NULL),
('MGA', 'Meghalaya', 'North Eastern', NULL),
('MzM', 'Mizoram', 'North Eastern', NULL),
('NGD', 'Nagaland', 'North Eastern', NULL),
('TPA', 'Tripura', 'North Eastern', NULL),

-- Western Region
('CTG', 'Chhattisgarh', 'Western', NULL),
('GOA', 'Goa', 'Western', NULL),
('GJT', 'Gujarat', 'Western', NULL),
('MPD', 'Madhya Pradesh', 'Western', NULL), -- Using 'MPD' as written above the line
('MHA', 'Maharashtra', 'Western', NULL),

-- Southern Region
('AP', 'Andhra Pradesh', 'Southern', NULL),
('KRT', 'Karnataka', 'Southern', NULL),
('KRL', 'Kerala', 'Southern', NULL),
('LKS', 'Lakshadweep', 'Southern', NULL),
('PU', 'Puducherry', 'Southern', NULL),
('TND', 'Tamil Nadu', 'Southern', NULL),
('TLG', 'Telangana', 'Southern', NULL),

-- Eastern Region
('ANI', 'Andaman and Nicobar Islands', 'Eastern', NULL),
('BHR', 'Bihar', 'Eastern', NULL),
('JHK', 'Jharkhand', 'Eastern', NULL),
('ODI', 'Odisha', 'Eastern', NULL),
('SKM', 'Sikkim', 'Eastern',NULL),
('BGL', 'West Bengal', 'Eastern', NULL);

-- Insert data into the ENERGYTYPE table
INSERT INTO ENERGYTYPE (Type_ID, Type_Name, Description)
VALUES 
('TGT', 'THER (CGT)', NULL),
('TH', 'THERMAL', NULL),
('HY', 'HYDRO', NULL),
('NU', 'NUCLEAR', NULL),
('WI', 'WIND', NULL),
('SO', 'SOLAR', NULL),
('BIO', 'BIOMASS', NULL);

-- Insert data into the SECTOR table
INSERT INTO SECTOR (Sector_ID, Sector_Name)
VALUES 
('PVT', 'Private'),
('CCT', 'Central'),
('ST', 'State');

