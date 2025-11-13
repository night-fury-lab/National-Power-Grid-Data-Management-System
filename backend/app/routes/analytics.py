from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import text

bp = Blueprint('analytics', __name__)

@bp.route('/regional-performance', methods=['GET'])
def get_regional_performance():
    """Get regional energy performance using the corrected stored procedure"""
    try:
        # Use the last 30 days for analytics
        query = text("""
            CALL sp_CalculateRegionalMetrics(
                DATE_SUB(CURDATE(), INTERVAL 30 DAY),
                CURDATE()
            )
        """)

        results = db.session.execute(query).fetchall()
        
        data = [{
            'region': row[0],
            'total_plants': int(row[1] or 0),
            'generated_mu': float(row[2] or 0),
            'demand_mu': float(row[3] or 0),
            'surplus_mu': float(row[2] or 0) - float(row[3] or 0),  # Calculate surplus
            'supply_percentage': float(row[4] or 0),
            'energy_status': 'Surplus' if float(row[2] or 0) >= float(row[3] or 0) else 'Deficit'
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in regional performance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/efficiency-comparison', methods=['GET'])
def get_efficiency_comparison():
    """Compare plant efficiency"""
    try:
        query = text("""
            SELECT 
                p.Plant_ID,
                p.Plant_Name,
                ROUND(AVG(pl.Efficiency_Percentage), 2) AS Avg_Efficiency
            FROM POWERPLANTS p
            LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            GROUP BY p.Plant_ID, p.Plant_Name
            ORDER BY Avg_Efficiency DESC
            LIMIT 20
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'plant_id': row[0],
            'plant_name': row[1],
            'avg_efficiency': float(row[2] or 0)
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/renewable-mix', methods=['GET'])
def get_renewable_mix():
    """Get renewable energy mix with MU values"""
    try:
        query = text("""
            WITH EnergyMix AS (
                SELECT 
                    s.State_Name,
                    s.Region,
                    fn_energy_category(et.Type_Name) AS Energy_Category,
                    SUM(pl.Todays_Actual_MU) AS Total_Production_MU
                FROM POWERPLANTS p
                INNER JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
                INNER JOIN STATE s ON p.State_Code = s.State_Code
                INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
                WHERE pl.Log_Date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY s.State_Name, s.Region, Energy_Category
            )
            SELECT 
                State_Name,
                Region,
                SUM(CASE WHEN Energy_Category = 'Renewable' THEN Total_Production_MU ELSE 0 END) AS Renewable_MU,
                SUM(CASE WHEN Energy_Category = 'Non-Renewable' THEN Total_Production_MU ELSE 0 END) AS Non_Renewable_MU,
                SUM(Total_Production_MU) AS Total_MU,
                fn_calculate_renewable_percentage(
                    SUM(CASE WHEN Energy_Category = 'Renewable' THEN Total_Production_MU ELSE 0 END),
                    SUM(Total_Production_MU)
                ) AS Renewable_Percentage
            FROM EnergyMix
            GROUP BY State_Name, Region
            ORDER BY Renewable_Percentage DESC
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'state_name': row[0],
            'region': row[1],
            'renewable_mu': float(row[2] or 0),
            'non_renewable_mu': float(row[3] or 0),
            'total_mu': float(row[4] or 0),
            'renewable_percentage': float(row[5] or 0)
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in renewable mix: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/monthly-trends', methods=['GET'])
def get_monthly_trends():
    """Get monthly energy production trends with growth rate"""
    try:
        query = text("""
            WITH MonthlyAgg AS (
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
            )
            SELECT 
                Month,
                Year,
                Type_Name,
                Monthly_Production_MU,
                Avg_Efficiency,
                Active_Plants,
                LAG(Monthly_Production_MU) OVER (
                    PARTITION BY Type_Name
                    ORDER BY Year, Month
                ) AS Previous_Month_Production,
                ROUND(
                    (
                        Monthly_Production_MU - LAG(Monthly_Production_MU) OVER (
                            PARTITION BY Type_Name
                            ORDER BY Year, Month
                        )
                    ) / NULLIF(LAG(Monthly_Production_MU) OVER (
                            PARTITION BY Type_Name
                            ORDER BY Year, Month
                        ), 0) * 100, 2
                ) AS Growth_Rate_Percentage
            FROM MonthlyAgg
            ORDER BY Year, Month, Type_Name
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'month': row[0],
            'year': row[1],
            'type_name': row[2],
            'monthly_production_mu': float(row[3] or 0),
            'avg_efficiency': float(row[4] or 0),
            'active_plants': row[5],
            'previous_month_production': float(row[6] or 0) if row[6] else None,
            'growth_rate_percentage': float(row[7] or 0) if row[7] else None
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in monthly trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
