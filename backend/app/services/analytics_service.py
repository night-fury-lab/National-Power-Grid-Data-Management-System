from app import db
from sqlalchemy import text
from datetime import datetime, timedelta

class AnalyticsService:
    
    @staticmethod
    def get_regional_performance(start_date=None, end_date=None):
        """Get regional energy performance analysis"""
        if not start_date:
            start_date = '2025-08-01'
        if not end_date:
            end_date = '2025-10-31'
        
        query = text("""
            SELECT 
                s.Region,
                COUNT(DISTINCT p.Plant_ID) AS Total_Plants,
                COALESCE(SUM(rd.Generated_MU), 0) AS Total_Generated_MU,
                COALESCE(SUM(rd.Demand_MU), 0) AS Total_Demand_MU,
                COALESCE(SUM(rd.Surplus_MU), 0) AS Total_Surplus_MU,
                COALESCE(SUM(rd.Imported_MU), 0) AS Total_Imported_MU,
                CASE 
                    WHEN SUM(rd.Generated_MU) >= SUM(rd.Demand_MU) THEN 'Surplus'
                    ELSE 'Deficit'
                END AS Energy_Status,
                ROUND(((SUM(rd.Generated_MU) / NULLIF(SUM(rd.Demand_MU), 0)) * 100), 2) AS Supply_Adequacy_Percentage
            FROM STATE s
            LEFT JOIN POWERPLANTS p ON s.State_Code = p.State_Code
            LEFT JOIN REGION_DETAILS rd ON s.State_Code = rd.State_Code
            WHERE rd.Report_Date >= :start_date AND rd.Report_Date <= :end_date
            GROUP BY s.Region
            ORDER BY Supply_Adequacy_Percentage DESC
        """)
        
        result = db.session.execute(query, {'start_date': start_date, 'end_date': end_date})
        
        return [{
            'region': row[0],
            'total_plants': row[1],
            'generated_mu': float(row[2] or 0),
            'demand_mu': float(row[3] or 0),
            'surplus_mu': float(row[4] or 0),
            'imported_mu': float(row[5] or 0),
            'energy_status': row[6],
            'supply_adequacy': float(row[7] or 0)
        } for row in result]
    
    @staticmethod
    def get_efficiency_comparison():
        """Compare plant performance against sector averages"""
        query = text("""
            WITH SectorAverages AS (
                SELECT 
                    p.Sector_ID,
                    AVG(pl.Efficiency_Percentage) AS Sector_Avg_Efficiency
                FROM POWERPLANTS p
                INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
                GROUP BY p.Sector_ID
            )
            SELECT 
                p.Plant_ID,
                p.Plant_Name,
                sec.Sector_Name,
                et.Type_Name,
                ROUND(AVG(pl.Efficiency_Percentage), 2) AS Plant_Avg_Efficiency,
                ROUND(sa.Sector_Avg_Efficiency, 2) AS Sector_Avg_Efficiency,
                ROUND((AVG(pl.Efficiency_Percentage) - sa.Sector_Avg_Efficiency), 2) AS Efficiency_Difference,
                CASE 
                    WHEN AVG(pl.Efficiency_Percentage) > sa.Sector_Avg_Efficiency THEN 'Above Average'
                    WHEN AVG(pl.Efficiency_Percentage) = sa.Sector_Avg_Efficiency THEN 'Average'
                    ELSE 'Below Average'
                END AS Performance_Rating
            FROM POWERPLANTS p
            INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            INNER JOIN SECTOR sec ON p.Sector_ID = sec.Sector_ID
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            INNER JOIN SectorAverages sa ON p.Sector_ID = sa.Sector_ID
            GROUP BY p.Plant_ID, p.Plant_Name, sec.Sector_Name, et.Type_Name, sa.Sector_Avg_Efficiency
            ORDER BY Efficiency_Difference DESC
            LIMIT 50
        """)
        
        result = db.session.execute(query)
        
        return [{
            'plant_id': row[0],
            'plant_name': row[1],
            'sector': row[2],
            'energy_type': row[3],
            'plant_efficiency': float(row[4] or 0),
            'sector_avg_efficiency': float(row[5] or 0),
            'efficiency_difference': float(row[6] or 0),
            'performance_rating': row[7]
        } for row in result]
    
    @staticmethod
    def get_renewable_energy_mix():
        """Get renewable vs non-renewable energy mix by state"""
        query = text("""
            WITH EnergyMix AS (
                SELECT 
                    s.State_Name,
                    s.Region,
                    CASE 
                        WHEN et.Type_Name IN ('HYDRO', 'WIND', 'SOLAR', 'BIOMASS') THEN 'Renewable'
                        ELSE 'Non-Renewable'
                    END AS Energy_Category,
                    SUM(pl.Todays_Actual_MU) AS Total_Production_MU
                FROM POWERPLANTS p
                INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
                INNER JOIN STATE s ON p.State_Code = s.State_Code
                INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
                GROUP BY s.State_Name, s.Region, Energy_Category
            )
            SELECT 
                State_Name,
                Region,
                SUM(CASE WHEN Energy_Category = 'Renewable' THEN Total_Production_MU ELSE 0 END) AS Renewable_MU,
                SUM(CASE WHEN Energy_Category = 'Non-Renewable' THEN Total_Production_MU ELSE 0 END) AS Non_Renewable_MU,
                SUM(Total_Production_MU) AS Total_MU,
                ROUND(
                    (SUM(CASE WHEN Energy_Category = 'Renewable' THEN Total_Production_MU ELSE 0 END) / 
                     NULLIF(SUM(Total_Production_MU), 0)) * 100, 2
                ) AS Renewable_Percentage
            FROM EnergyMix
            GROUP BY State_Name, Region
            ORDER BY Renewable_Percentage DESC
        """)
        
        result = db.session.execute(query)
        
        return [{
            'state_name': row[0],
            'region': row[1],
            'renewable_mu': float(row[2] or 0),
            'non_renewable_mu': float(row[3] or 0),
            'total_mu': float(row[4] or 0),
            'renewable_percentage': float(row[5] or 0)
        } for row in result]
    
    @staticmethod
    def get_monthly_trends():
        """Get monthly production trends"""
        query = text("""
            SELECT 
                d.Month,
                d.Year,
                et.Type_Name,
                SUM(pl.Todays_Actual_MU) AS Monthly_Production_MU,
                AVG(pl.Efficiency_Percentage) AS Avg_Efficiency,
                COUNT(DISTINCT p.Plant_ID) AS Active_Plants
            FROM PRODUCTIONLOG pl
            INNER JOIN POWERPLANTS p ON pl.Plant_ID = p.Plant_ID
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            INNER JOIN DATE_DIM d ON pl.Log_Date = d.Date
            GROUP BY d.Month, d.Year, et.Type_Name
            ORDER BY d.Year, d.Month, et.Type_Name
        """)
        
        result = db.session.execute(query)
        
        return [{
            'month': row[0],
            'year': row[1],
            'energy_type': row[2],
            'production_mu': float(row[3] or 0),
            'avg_efficiency': float(row[4] or 0),
            'active_plants': row[5]
        } for row in result]
