from app import db
from sqlalchemy import text
from datetime import datetime, timedelta

class AlertService:
    
    @staticmethod
    def get_all_alerts():
        """Get all system alerts"""
        query = text("""
            SELECT 
                'Low Efficiency' AS Alert_Type,
                p.Plant_Name,
                s.State_Name,
                ROUND(AVG(pl.Efficiency_Percentage), 2) AS Value,
                'WARNING' AS Severity,
                MAX(pl.Log_Date) AS Last_Occurrence
            FROM POWERPLANTS p
            INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            INNER JOIN STATE s ON p.State_Code = s.State_Code
            WHERE pl.Log_Date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
            GROUP BY p.Plant_ID, p.Plant_Name, s.State_Name
            HAVING AVG(pl.Efficiency_Percentage) < 60

            UNION ALL

            SELECT 
                'Critical Coal Stock' AS Alert_Type,
                p.Plant_Name,
                s.State_Name,
                pl.Coal_Stock_Days AS Value,
                fn_coal_stock_severity(pl.Coal_Stock_Days) AS Severity,
                pl.Log_Date AS Last_Occurrence
            FROM POWERPLANTS p
            INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            INNER JOIN STATE s ON p.State_Code = s.State_Code
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            WHERE pl.Log_Date = (SELECT MAX(Log_Date) FROM PRODUCTIONLOG WHERE Plant_ID = p.Plant_ID)
                AND et.Type_Name IN ('THERMAL', 'THER (CGT)')
                AND pl.Coal_Stock_Days < 7

            UNION ALL

            SELECT 
                'Plant Outage' AS Alert_Type,
                p.Plant_Name,
                s.State_Name,
                os.Cap_Under_Outage_MW AS Value,
                CASE 
                    WHEN os.Cap_Under_Outage_MW >= 500 THEN 'CRITICAL'
                    ELSE 'WARNING'
                END AS Severity,
                os.Status_Date AS Last_Occurrence
            FROM POWERPLANTS p
            INNER JOIN OPERATIONAL_STATUS os ON p.Plant_ID = os.Plant_ID
            INNER JOIN STATE s ON p.State_Code = s.State_Code
            WHERE os.Status = 'Under Outage'
                AND os.Status_Date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)

            ORDER BY Severity DESC, Last_Occurrence DESC
        """)
        
        result = db.session.execute(query)
        
        return [{
            'alert_type': row[0],
            'plant_name': row[1],
            'state_name': row[2],
            'value': float(row[3] or 0),
            'severity': row[4],
            'last_occurrence': str(row[5])
        } for row in result]
    
    @staticmethod
    def get_coal_critical_alerts():
        """Get plants with critical coal stock"""
        query = text("""
            SELECT 
                p.Plant_ID,
                p.Plant_Name,
                s.State_Name,
                sec.Sector_Name,
                pl.Log_Date,
                pl.Coal_Stock_Days,
                pl.Operational_Capacity_MW,
                fn_coal_stock_severity(pl.Coal_Stock_Days) AS Severity
            FROM POWERPLANTS p
            INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            INNER JOIN STATE s ON p.State_Code = s.State_Code
            INNER JOIN SECTOR sec ON p.Sector_ID = sec.Sector_ID
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            WHERE et.Type_Name IN ('THERMAL', 'THER (CGT)')
                AND pl.Coal_Stock_Days IS NOT NULL
                AND pl.Log_Date = (SELECT MAX(Log_Date) FROM PRODUCTIONLOG WHERE Plant_ID = p.Plant_ID)
                AND pl.Coal_Stock_Days < 7
            ORDER BY pl.Coal_Stock_Days ASC, pl.Operational_Capacity_MW DESC
        """)
        
        result = db.session.execute(query)
        
        return [{
            'plant_id': row[0],
            'plant_name': row[1],
            'state_name': row[2],
            'sector_name': row[3],
            'log_date': str(row[4]),
            'coal_stock_days': float(row[5] or 0),
            'capacity_mw': float(row[6] or 0),
            'stock_status': row[7]
        } for row in result]
    
    @staticmethod
    def get_alert_count():
        """Get count of alerts by severity"""
        alerts = AlertService.get_all_alerts()
        
        critical = len([a for a in alerts if a['severity'] == 'CRITICAL'])
        warning = len([a for a in alerts if a['severity'] == 'WARNING'])
        
        return {
            'total': len(alerts),
            'critical': critical,
            'warning': warning
        }
