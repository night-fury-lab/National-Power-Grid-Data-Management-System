from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import text

bp = Blueprint('regions', __name__)

@bp.route('/', methods=['GET'])
def get_all_regions():
    """Get all regions with energy statistics"""
    try:
        # Get optional date parameter
        selected_date = request.args.get('date')
        
        if selected_date:
            # Query for specific date - use REGION_DETAILS as primary source to avoid row multiplication
            query = text("""
                SELECT 
                    rd.State_Code,
                    s.State_Name,
                    s.Region,
                    (SELECT COUNT(DISTINCT Plant_ID) FROM POWERPLANTS WHERE State_Code = rd.State_Code) AS Plant_Count,
                    COALESCE(rd.Generated_MU, 0) AS Generated_MU,
                    COALESCE(rd.Demand_MU, 0) AS Demand_MU,
                    CASE 
                        WHEN COALESCE(rd.Generated_MU, 0) >= COALESCE(rd.Demand_MU, 0) THEN 'Surplus'
                        ELSE 'Deficit'
                    END AS Energy_Status
                FROM REGION_DETAILS rd
                INNER JOIN STATE s ON rd.State_Code = s.State_Code
                WHERE rd.Report_Date = :selected_date
                ORDER BY s.Region, s.State_Name
            """)
            results = db.session.execute(query, {'selected_date': selected_date}).fetchall()
        else:
            # Query for all dates (aggregated) - sum across all dates in REGION_DETAILS
            query = text("""
                SELECT 
                    rd.State_Code,
                    s.State_Name,
                    s.Region,
                    (SELECT COUNT(DISTINCT Plant_ID) FROM POWERPLANTS WHERE State_Code = rd.State_Code) AS Plant_Count,
                    COALESCE(SUM(rd.Generated_MU), 0) AS Generated_MU,
                    COALESCE(SUM(rd.Demand_MU), 0) AS Demand_MU,
                    CASE 
                        WHEN SUM(rd.Generated_MU) >= SUM(rd.Demand_MU) THEN 'Surplus'
                        ELSE 'Deficit'
                    END AS Energy_Status
                FROM REGION_DETAILS rd
                INNER JOIN STATE s ON rd.State_Code = s.State_Code
                GROUP BY rd.State_Code, s.State_Name, s.Region
                ORDER BY s.Region, s.State_Name
            """)
            results = db.session.execute(query).fetchall()
        
        data = [{
            'state_code': row[0],
            'state_name': row[1],
            'region': row[2],
            'plant_count': row[3],
            'generated_mu': float(row[4] or 0),
            'demand_mu': float(row[5] or 0),
            'energy_status': row[6] or 'Unknown'
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in get_all_regions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/available-dates', methods=['GET'])
def get_available_dates():
    """Get list of available report dates from REGION_DETAILS"""
    try:
        query = text("""
            SELECT DISTINCT Report_Date
            FROM REGION_DETAILS
            ORDER BY Report_Date DESC
            LIMIT 30
        """)
        
        results = db.session.execute(query).fetchall()
        dates = [str(row[0]) for row in results if row[0]]
        
        return jsonify({'success': True, 'data': dates}), 200
        
    except Exception as e:
        print(f"Error in get_available_dates: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<state_code>/energy-mix', methods=['GET'])
def get_state_energy_mix(state_code):
    """Get energy mix distribution for a specific state"""
    try:
        # Get optional date parameter
        selected_date = request.args.get('date')
        
        if selected_date:
            # Query for specific date
            query = text("""
                SELECT 
                    et.Type_Name,
                    COALESCE(SUM(pl.Todays_Actual_MU), 0) AS Total_Generated_MU
                FROM POWERPLANTS p
                INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
                LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID AND pl.Log_Date = :selected_date
                WHERE p.State_Code = :state_code
                GROUP BY et.Type_Name
                HAVING Total_Generated_MU > 0
                ORDER BY Total_Generated_MU DESC
            """)
            results = db.session.execute(query, {'state_code': state_code, 'selected_date': selected_date}).fetchall()
        else:
            # Query for all dates (aggregated)
            query = text("""
                SELECT 
                    et.Type_Name,
                    COALESCE(SUM(pl.Todays_Actual_MU), 0) AS Total_Generated_MU
                FROM POWERPLANTS p
                INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
                LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
                WHERE p.State_Code = :state_code
                GROUP BY et.Type_Name
                HAVING Total_Generated_MU > 0
                ORDER BY Total_Generated_MU DESC
            """)
            results = db.session.execute(query, {'state_code': state_code}).fetchall()
        
        if not results:
            return jsonify({'success': False, 'error': 'No energy mix data found for this state'}), 404
        
        data = [{
            'energy_type': row[0],
            'generated_mu': float(row[1] or 0)
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in get_state_energy_mix: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<state_code>/details', methods=['GET'])
def get_state_details(state_code):
    """Get state details"""
    try:
        query = text("""
            SELECT 
                s.State_Name,
                s.Region,
                s.Population,
                COUNT(DISTINCT p.Plant_ID) AS Total_Plants
            FROM STATE s
            LEFT JOIN POWERPLANTS p ON s.State_Code = p.State_Code
            WHERE s.State_Code = :state_code
            GROUP BY s.State_Name, s.Region, s.Population
        """)
        
        result = db.session.execute(query, {'state_code': state_code}).fetchone()
        
        if not result:
            return jsonify({'success': False, 'error': 'State not found'}), 404
        
        data = {
            'state_name': result[0],
            'region': result[1],
            'population': result[2],
            'total_plants': result[3]
        }
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
