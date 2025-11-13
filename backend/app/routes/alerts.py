from flask import Blueprint, jsonify
from app import db
from sqlalchemy import text

bp = Blueprint('alerts', __name__)

@bp.route('/', methods=['GET'])
def get_all_alerts():
    """Get all system alerts - matches comprehensive_queries.sql"""
    try:
        # Low Efficiency Alerts
        low_efficiency_query = text("""
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
        """)
        
        low_efficiency = db.session.execute(low_efficiency_query).fetchall()
        
        # Critical Coal Stock Alerts
        coal_query = text("""
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
        """)
        
        coal_alerts = db.session.execute(coal_query).fetchall()
        
        # Plant Outage Alerts
        outage_query = text("""
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
        """)
        
        outage_alerts = db.session.execute(outage_query).fetchall()
        
        # Combine all alerts
        alerts = []
        
        for row in low_efficiency:
            alerts.append({
                'alert_type': row[0],
                'plant_name': row[1],
                'state_name': row[2],
                'value': float(row[3] or 0),
                'severity': row[4],
                'last_occurrence': str(row[5])
            })
        
        for row in coal_alerts:
            alerts.append({
                'alert_type': row[0],
                'plant_name': row[1],
                'state_name': row[2],
                'value': float(row[3] or 0),
                'severity': row[4],
                'last_occurrence': str(row[5])
            })
        
        for row in outage_alerts:
            alerts.append({
                'alert_type': row[0],
                'plant_name': row[1],
                'state_name': row[2],
                'value': float(row[3] or 0),
                'severity': row[4],
                'last_occurrence': str(row[5])
            })
        
        # Sort by severity (CRITICAL > WARNING > INFO) and last occurrence
        severity_order = {'CRITICAL': 0, 'WARNING': 1, 'INFO': 2}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 99), x['last_occurrence']), reverse=True)
        
        return jsonify({'success': True, 'data': alerts}), 200
        
    except Exception as e:
        print(f"Error in get_all_alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/coal-critical', methods=['GET'])
def get_coal_critical():
    """Get critical coal stock alerts - matches comprehensive_queries.sql"""
    try:
        query = text("""
            SELECT 
                p.Plant_ID,
                p.Plant_Name,
                s.State_Name,
                sec.Sector_Name,
                pl.Log_Date,
                pl.Coal_Stock_Days,
                pl.Operational_Capacity_MW,
                pl.Todays_Actual_MU,
                CASE 
                    WHEN pl.Coal_Stock_Days < 4 THEN 'CRITICAL'
                    WHEN pl.Coal_Stock_Days < 7 THEN 'WARNING'
                    ELSE 'ADEQUATE'
                END AS Stock_Status,
                (SELECT AVG(pl2.Coal_Stock_Days) 
                 FROM PRODUCTIONLOG pl2 
                 WHERE pl2.Plant_ID = p.Plant_ID) AS Avg_Coal_Stock_Days
            FROM POWERPLANTS p
            INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            INNER JOIN STATE s ON p.State_Code = s.State_Code
            INNER JOIN SECTOR sec ON p.Sector_ID = sec.Sector_ID
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            WHERE et.Type_Name IN ('THERMAL', 'THER (CGT)')
                AND pl.Coal_Stock_Days IS NOT NULL
                AND pl.Log_Date = (
                    SELECT MAX(Log_Date) 
                    FROM PRODUCTIONLOG 
                    WHERE Plant_ID = p.Plant_ID
                )
            ORDER BY pl.Coal_Stock_Days ASC, pl.Operational_Capacity_MW DESC
            LIMIT 20
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'plant_id': row[0],
            'plant_name': row[1],
            'state_name': row[2],
            'sector_name': row[3],
            'log_date': str(row[4]),
            'coal_stock_days': float(row[5] or 0),
            'operational_capacity_mw': float(row[6] or 0),
            'todays_actual_mu': float(row[7] or 0),
            'stock_status': row[8],
            'avg_coal_stock_days': float(row[9] or 0) if row[9] else None
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in get_coal_critical: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
