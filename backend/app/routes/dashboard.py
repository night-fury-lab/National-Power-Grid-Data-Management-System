from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import text

bp = Blueprint('dashboard', __name__)

@bp.route('/overview', methods=['GET'])
def get_dashboard_overview():
    """Get main dashboard KPIs and metrics"""
    try:
        # total plants
        plants_query = text("SELECT COUNT(DISTINCT Plant_ID) FROM POWERPLANTS")
        total_plants = db.session.execute(plants_query).scalar() or 0

        # Accept optional date param (YYYY-MM-DD). If not provided, choose latest date where all plants have production logs
        date_param = request.args.get('date')
        if date_param:
            try:
                selected_date = date_param
            except Exception:
                selected_date = None
        else:
            # Prefer a date where all plants have production entries. Use a grouped query for efficiency.
            selected_date = None
            if total_plants > 0:
                complete_coverage_query = text(
                    "SELECT Log_Date FROM PRODUCTIONLOG GROUP BY Log_Date HAVING COUNT(DISTINCT Plant_ID) = :total ORDER BY Log_Date DESC LIMIT 1"
                )
                selected_date = db.session.execute(complete_coverage_query, {'total': total_plants}).scalar()
            # If no complete-coverage date found, fall back to latest DATE_DIM that has logs, or latest production log
            if not selected_date:
                last_date_with_logs_query = text(
                    "SELECT MAX(d.`Date`) FROM DATE_DIM d WHERE EXISTS (SELECT 1 FROM PRODUCTIONLOG pl WHERE pl.Log_Date = d.`Date`)"
                )
                selected_date = db.session.execute(last_date_with_logs_query).scalar()
                if not selected_date:
                    last_log_date_query = text("SELECT MAX(Log_Date) FROM PRODUCTIONLOG")
                    selected_date = db.session.execute(last_log_date_query).scalar()

        # If no date found, return zeros
        if not selected_date:
            data = {
                'total_plants': total_plants,
                'selected_date': None,
                'todays_generation_mu': 0.0,
                'todays_demand_mu': 0.0,
                'avg_efficiency': 0.0,
                'total_capacity_mw': 0.0,
                'plants_under_outage': 0,
                'critical_coal_alerts': 0,
                'energy_balance': 'Unknown',
                'date_filter_placeholder': '2025-08-01'
            }
            return jsonify({'success': True, 'data': data}), 200

        # Ensure selected_date is a string in YYYY-MM-DD format
        selected_date_str = str(selected_date)

        # Sum generation for the selected date
        generation_query = text("SELECT COALESCE(SUM(Todays_Actual_MU), 0) FROM PRODUCTIONLOG WHERE Log_Date = :log_date")
        generation = float(db.session.execute(generation_query, {'log_date': selected_date_str}).scalar() or 0)

        # Average efficiency for that date
        efficiency_query = text("SELECT ROUND(AVG(Efficiency_Percentage), 2) FROM PRODUCTIONLOG WHERE Log_Date = :log_date")
        efficiency = float(db.session.execute(efficiency_query, {'log_date': selected_date_str}).scalar() or 0)

        # Total capacity for that date
        capacity_query = text("SELECT COALESCE(SUM(Operational_Capacity_MW), 0) FROM PRODUCTIONLOG WHERE Log_Date = :log_date")
        capacity = float(db.session.execute(capacity_query, {'log_date': selected_date_str}).scalar() or 0)

        # Plants under outage on that date (use Status_Date)
        outage_query = text("SELECT COUNT(DISTINCT Plant_ID) FROM OPERATIONAL_STATUS WHERE Status_Date = :status_date AND Status = 'Under Outage'")
        plants_under_outage = db.session.execute(outage_query, {'status_date': selected_date_str}).scalar() or 0

        # Critical coal alerts for that date
        coal_query = text("""
            SELECT COUNT(*) 
            FROM PRODUCTIONLOG pl
            INNER JOIN POWERPLANTS p ON pl.Plant_ID = p.Plant_ID
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            WHERE pl.Log_Date = :log_date
            AND et.Type_Name IN ('THERMAL', 'THER (CGT)')
            AND pl.Coal_Stock_Days < 7
        """)
        critical_coal_alerts = db.session.execute(coal_query, {'log_date': selected_date_str}).scalar() or 0

        # Demand from REGION_DETAILS for that date
        demand_query = text("SELECT COALESCE(SUM(Demand_MU), 0) FROM REGION_DETAILS WHERE Report_Date = :report_date")
        todays_demand = float(db.session.execute(demand_query, {'report_date': selected_date_str}).scalar() or 0)

        data = {
            'total_plants': total_plants,
            'selected_date': selected_date_str,
            'todays_generation_mu': generation,
            'todays_demand_mu': todays_demand,
            'avg_efficiency': efficiency,
            'total_capacity_mw': capacity,
            'plants_under_outage': plants_under_outage,
            'critical_coal_alerts': critical_coal_alerts,
            'energy_balance': 'Surplus' if generation >= todays_demand else 'Deficit',
            'date_filter_placeholder': '2025-08-01'
        }

        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in dashboard overview: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/energy-mix', methods=['GET'])
def get_energy_mix():
    """Get energy type distribution for last 30 days"""
    try:
        # For dashboard we want energy mix for a specific date (default to latest in DATE_DIM)
        date_param = request.args.get('date')
        # total plants (needed when attempting to find a complete-coverage date)
        plants_query = text("SELECT COUNT(DISTINCT Plant_ID) FROM POWERPLANTS")
        total_plants = db.session.execute(plants_query).scalar() or 0
        if date_param:
            selected_date = date_param
        else:
            # Prefer a date where all plants have production entries. Use a grouped query for efficiency.
            selected_date = None
            if total_plants > 0:
                complete_coverage_query = text(
                    "SELECT Log_Date FROM PRODUCTIONLOG GROUP BY Log_Date HAVING COUNT(DISTINCT Plant_ID) = :total ORDER BY Log_Date DESC LIMIT 1"
                )
                selected_date = db.session.execute(complete_coverage_query, {'total': total_plants}).scalar()
            if not selected_date:
                last_date_with_logs_query = text(
                    "SELECT MAX(d.`Date`) FROM DATE_DIM d WHERE EXISTS (SELECT 1 FROM PRODUCTIONLOG pl WHERE pl.Log_Date = d.`Date`)"
                )
                selected_date = db.session.execute(last_date_with_logs_query).scalar()
                if not selected_date:
                    last_log_date_query = text("SELECT MAX(Log_Date) FROM PRODUCTIONLOG")
                    selected_date = db.session.execute(last_log_date_query).scalar()

        if not selected_date:
            return jsonify({'success': True, 'data': []}), 200

        selected_date_str = str(selected_date)

        query = text("""
            SELECT 
                COALESCE(et.Type_Name, 'Unknown') as type_name,
                COUNT(DISTINCT p.Plant_ID) as plant_count,
                COALESCE(SUM(pl.Todays_Actual_MU), 0) as total_generation_mu,
                COALESCE(ROUND(AVG(pl.Efficiency_Percentage), 2), 0) as avg_efficiency
            FROM ENERGYTYPE et
            LEFT JOIN POWERPLANTS p ON et.Type_ID = p.Type_ID
            LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID 
                AND pl.Log_Date = :log_date
            WHERE et.Type_ID IS NOT NULL
            GROUP BY et.Type_Name
            HAVING SUM(pl.Todays_Actual_MU) > 0
            ORDER BY total_generation_mu DESC
        """)

        results = db.session.execute(query, {'log_date': selected_date_str}).fetchall()

        data = [{
            'type_name': row[0] or 'Unknown',
            'plant_count': row[1],
            'total_generation_mu': float(row[2] or 0),
            'avg_efficiency': float(row[3] or 0)
        } for row in results]

        return jsonify({'success': True, 'selected_date': selected_date_str, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in energy mix: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/top-performers', methods=['GET'])
def get_top_performers():
    """Get top performing plants"""
    try:
        # Make top performers date-based (defaults to latest date in DATE_DIM)
        date_param = request.args.get('date')
        # total plants (needed when attempting to find a complete-coverage date)
        plants_query = text("SELECT COUNT(DISTINCT Plant_ID) FROM POWERPLANTS")
        total_plants = db.session.execute(plants_query).scalar() or 0
        if date_param:
            selected_date = date_param
        else:
            # Prefer a date where all plants have production entries. Use a grouped query for efficiency.
            selected_date = None
            if total_plants > 0:
                complete_coverage_query = text(
                    "SELECT Log_Date FROM PRODUCTIONLOG GROUP BY Log_Date HAVING COUNT(DISTINCT Plant_ID) = :total ORDER BY Log_Date DESC LIMIT 1"
                )
                selected_date = db.session.execute(complete_coverage_query, {'total': total_plants}).scalar()
            if not selected_date:
                last_date_with_logs_query = text(
                    "SELECT MAX(d.`Date`) FROM DATE_DIM d WHERE EXISTS (SELECT 1 FROM PRODUCTIONLOG pl WHERE pl.Log_Date = d.`Date`)"
                )
                selected_date = db.session.execute(last_date_with_logs_query).scalar()
                if not selected_date:
                    last_log_date_query = text("SELECT MAX(Log_Date) FROM PRODUCTIONLOG")
                    selected_date = db.session.execute(last_log_date_query).scalar()

        if not selected_date:
            return jsonify({'success': True, 'data': []}), 200

        selected_date_str = str(selected_date)

        query = text("""
            SELECT 
                p.Plant_ID,
                p.Plant_Name,
                s.State_Name,
                et.Type_Name,
                COALESCE(ROUND(pl.Efficiency_Percentage, 2), 0) as efficiency,
                COALESCE(ROUND(pl.Todays_Actual_MU, 2), 0) as todays_generation_mu
            FROM POWERPLANTS p
            LEFT JOIN STATE s ON p.State_Code = s.State_Code
            LEFT JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID AND pl.Log_Date = :log_date
            WHERE pl.Log_Date = :log_date
            ORDER BY efficiency DESC
            LIMIT 10
        """)

        results = db.session.execute(query, {'log_date': selected_date_str}).fetchall()

        data = [{
            'plant_id': row[0],
            'plant_name': row[1],
            'state_name': row[2] or 'Unknown',
            'energy_type': row[3] or 'Unknown',
            'efficiency': float(row[4] or 0),
            'todays_generation_mu': float(row[5] or 0)
        } for row in results]

        return jsonify({'success': True, 'selected_date': selected_date_str, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in top performers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/weekly-trend', methods=['GET'])
def get_weekly_trend():
    """Get weekly energy trend data"""
    try:
        query = text("""
            SELECT 
                DATE(pl.Log_Date) AS Date,
                DAYNAME(pl.Log_Date) AS Day_Name,
                SUM(pl.Todays_Actual_MU) AS Total_Generation_MU,
                AVG(pl.Efficiency_Percentage) AS Avg_Efficiency,
                SUM(pl.Operational_Capacity_MW) AS Total_Capacity_MW,
                COUNT(DISTINCT pl.Plant_ID) AS Active_Plants,
                (SELECT SUM(Demand_MU) 
                 FROM REGION_DETAILS 
                 WHERE Report_Date = pl.Log_Date) AS Total_Demand_MU
            FROM PRODUCTIONLOG pl
            WHERE pl.Log_Date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(pl.Log_Date), DAYNAME(pl.Log_Date)
            ORDER BY Date
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'date': str(row[0]),
            'day_name': row[1],
            'total_generation_mu': float(row[2] or 0),
            'avg_efficiency': float(row[3] or 0),
            'total_capacity_mw': float(row[4] or 0),
            'active_plants': row[5],
            'total_demand_mu': float(row[6] or 0)
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in weekly trend: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
