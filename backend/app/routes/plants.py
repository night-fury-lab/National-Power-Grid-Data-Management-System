from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import text
bp = Blueprint('plants', __name__)

@bp.route('/', methods=['GET'])
def get_all_plants():
    """Get all power plants"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str).strip()
        state_code = request.args.get('state', '', type=str).strip()
        sector_id = request.args.get('sector', '', type=str).strip()
        type_id = request.args.get('type', '', type=str).strip()

        # Build WHERE clause conditions
        where_conditions = []
        params = {}
        
        if search:
            where_conditions.append("(UPPER(Plant_Name) LIKE UPPER(:search) OR UPPER(Plant_ID) LIKE UPPER(:search))")
            params['search'] = f"%{search}%"
        
        if state_code:
            where_conditions.append("State_Code = :state_code")
            params['state_code'] = state_code
        
        if sector_id:
            where_conditions.append("Sector_ID = :sector_id")
            params['sector_id'] = sector_id
        
        if type_id:
            where_conditions.append("Type_ID = :type_id")
            params['type_id'] = type_id
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Total count (with filters)
        count_query = text(f"""
            SELECT COUNT(*)
            FROM POWERPLANTS
            WHERE {where_clause}
        """)
        total = db.session.execute(count_query, params).scalar() or 0

        # Data query (with filters)
        data_query = text(f"""
            SELECT 
                Plant_ID, Plant_Name, State_Code, Sector_ID, Type_ID
            FROM POWERPLANTS
            WHERE {where_clause}
            ORDER BY Plant_Name
            LIMIT :limit OFFSET :offset
        """)
        params['limit'] = per_page
        params['offset'] = (page - 1) * per_page

        results = db.session.execute(data_query, params).fetchall()
        
        print(f"Filters - Search: '{search}', State: '{state_code}', Sector: '{sector_id}', Type: '{type_id}'")
        print(f"Found {len(results)} results, Total: {total}")
        
        data = [{
            'Plant_ID': row[0],
            'Plant_Name': row[1],
            'State_Code': row[2],
            'Sector_ID': row[3],
            'Type_ID': row[4]
        } for row in results]
        
        pages = max(1, (total + per_page - 1) // per_page)

        return jsonify({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<plant_id>', methods=['GET'])
def get_plant(plant_id):
    """Get comprehensive plant details - matches comprehensive_queries.sql"""
    try:
        # Get optional date parameter from query string
        selected_date = request.args.get('date')
        
        # Get basic plant information with region
        if selected_date:
            # Query for a specific date
            query = text("""
                SELECT 
                    p.Plant_ID,
                    p.Plant_Name,
                    s.State_Name,
                    s.Region,
                    sec.Sector_Name,
                    et.Type_Name,
                    et.Description,
                    (SELECT AVG(Efficiency_Percentage) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID AND Log_Date = :selected_date) AS Avg_Efficiency,
                    (SELECT SUM(Todays_Actual_MU) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID AND Log_Date = :selected_date) AS Total_Generation_MU,
                    (SELECT AVG(Operational_Capacity_MW) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID AND Log_Date = :selected_date) AS Avg_Capacity_MW,
                    (SELECT MAX(Log_Date) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID) AS Last_Log_Date,
                    (SELECT Status 
                     FROM OPERATIONAL_STATUS 
                     WHERE Plant_ID = p.Plant_ID 
                     AND Status_Date = :selected_date
                     LIMIT 1) AS Current_Status,
                    (SELECT Remarks 
                     FROM OPERATIONAL_STATUS 
                     WHERE Plant_ID = p.Plant_ID 
                     AND Status_Date = :selected_date
                     LIMIT 1) AS Status_Remarks,
                    (SELECT Outage_Date 
                     FROM OPERATIONAL_STATUS 
                     WHERE Plant_ID = p.Plant_ID 
                     AND Status_Date = :selected_date
                     LIMIT 1) AS Outage_Date
                FROM POWERPLANTS p
                INNER JOIN STATE s ON p.State_Code = s.State_Code
                INNER JOIN SECTOR sec ON p.Sector_ID = sec.Sector_ID
                INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
                WHERE p.Plant_ID = :plant_id
            """)
            result = db.session.execute(query, {'plant_id': plant_id, 'selected_date': selected_date}).fetchone()
        else:
            # Query for most recent date
            query = text("""
                SELECT 
                    p.Plant_ID,
                    p.Plant_Name,
                    s.State_Name,
                    s.Region,
                    sec.Sector_Name,
                    et.Type_Name,
                    et.Description,
                    (SELECT AVG(Efficiency_Percentage) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID) AS Avg_Efficiency,
                    (SELECT SUM(Todays_Actual_MU) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID) AS Total_Generation_MU,
                    (SELECT AVG(Operational_Capacity_MW) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID) AS Avg_Capacity_MW,
                    (SELECT MAX(Log_Date) 
                     FROM PRODUCTIONLOG 
                     WHERE Plant_ID = p.Plant_ID) AS Last_Log_Date,
                    (SELECT Status 
                     FROM OPERATIONAL_STATUS 
                     WHERE Plant_ID = p.Plant_ID 
                     AND Status_Date = (SELECT MAX(Log_Date) FROM PRODUCTIONLOG WHERE Plant_ID = p.Plant_ID)
                     LIMIT 1) AS Current_Status,
                    (SELECT Remarks 
                     FROM OPERATIONAL_STATUS 
                     WHERE Plant_ID = p.Plant_ID 
                     AND Status_Date = (SELECT MAX(Log_Date) FROM PRODUCTIONLOG WHERE Plant_ID = p.Plant_ID)
                     LIMIT 1) AS Status_Remarks,
                    (SELECT Outage_Date 
                     FROM OPERATIONAL_STATUS 
                     WHERE Plant_ID = p.Plant_ID 
                     AND Status_Date = (SELECT MAX(Log_Date) FROM PRODUCTIONLOG WHERE Plant_ID = p.Plant_ID)
                     LIMIT 1) AS Outage_Date
                FROM POWERPLANTS p
                INNER JOIN STATE s ON p.State_Code = s.State_Code
                INNER JOIN SECTOR sec ON p.Sector_ID = sec.Sector_ID
                INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
                WHERE p.Plant_ID = :plant_id
            """)
            result = db.session.execute(query, {'plant_id': plant_id}).fetchone()
        
        if not result:
            return jsonify({'success': False, 'error': 'Plant not found'}), 404
        
        data = {
            'plant_id': result[0],
            'plant_name': result[1],
            'state_name': result[2],
            'region': result[3] or 'Unknown',
            'sector_name': result[4],
            'energy_type': result[5],
            'description': result[6],
            'avg_efficiency': float(result[7] or 0),
            'total_generation_mu': float(result[8] or 0),
            'avg_capacity_mw': float(result[9] or 0),
            'last_log_date': str(result[10]) if result[10] else None,
            'current_status': result[11] or 'Unknown',
            'status_remarks': result[12] if result[12] else None,
            'outage_date': str(result[13]) if result[13] else None
        }
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        print(f"Error in get_plant: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/', methods=['POST'])
def create_plant():
    """Create a new power plant"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['Plant_ID', 'Plant_Name', 'State_Code', 'Sector_ID', 'Type_ID']):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        query = text("""
            INSERT INTO POWERPLANTS (Plant_ID, Plant_Name, State_Code, Sector_ID, Type_ID)
            VALUES (:plant_id, :plant_name, :state_code, :sector_id, :type_id)
        """)
        
        db.session.execute(query, {
            'plant_id': data['Plant_ID'],
            'plant_name': data['Plant_Name'],
            'state_code': data['State_Code'],
            'sector_id': data['Sector_ID'],
            'type_id': data['Type_ID']
        })
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Plant created successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<plant_id>', methods=['PUT'])
def update_plant(plant_id):
    """Update plant information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        update_fields = []
        params = {'plant_id': plant_id}
        
        if 'Plant_Name' in data:
            update_fields.append('Plant_Name = :plant_name')
            params['plant_name'] = data['Plant_Name']
        if 'State_Code' in data:
            update_fields.append('State_Code = :state_code')
            params['state_code'] = data['State_Code']
        if 'Sector_ID' in data:
            update_fields.append('Sector_ID = :sector_id')
            params['sector_id'] = data['Sector_ID']
        if 'Type_ID' in data:
            update_fields.append('Type_ID = :type_id')
            params['type_id'] = data['Type_ID']
        
        if not update_fields:
            return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
        query = text(f"""
            UPDATE POWERPLANTS
            SET {', '.join(update_fields)}
            WHERE Plant_ID = :plant_id
        """)
        
        db.session.execute(query, params)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Plant updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<plant_id>', methods=['DELETE'])
def delete_plant(plant_id):
    """Delete a power plant"""
    try:
        # Delete related production logs first
        delete_logs = text("DELETE FROM PRODUCTIONLOG WHERE Plant_ID = :plant_id")
        db.session.execute(delete_logs, {'plant_id': plant_id})
        
        # Delete operational status records
        delete_status = text("DELETE FROM OPERATIONAL_STATUS WHERE Plant_ID = :plant_id")
        db.session.execute(delete_status, {'plant_id': plant_id})
        
        # Delete the plant
        delete_plant_query = text("DELETE FROM POWERPLANTS WHERE Plant_ID = :plant_id")
        result = db.session.execute(delete_plant_query, {'plant_id': plant_id})
        db.session.commit()
        
        if result.rowcount == 0:
            return jsonify({'success': False, 'error': 'Plant not found'}), 404
        
        return jsonify({'success': True, 'message': 'Plant deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<plant_id>/production-history', methods=['GET'])
def get_production_history(plant_id):
    """Get production history for a plant"""
    try:
        days = request.args.get('days', 30, type=int)
        
        query = text("""
            SELECT 
                Log_Date,
                Efficiency_Percentage,
                Todays_Actual_MU,
                Capable_Generation_MU,
                Operational_Capacity_MW,
                Coal_Stock_Days
            FROM PRODUCTIONLOG
            WHERE Plant_ID = :plant_id
            AND Log_Date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            ORDER BY Log_Date DESC
        """)
        
        results = db.session.execute(query, {'plant_id': plant_id, 'days': days}).fetchall()
        
        data = [{
            'log_date': str(row[0]),
            'efficiency_percentage': float(row[1] or 0),
            'todays_actual_mu': float(row[2] or 0),
            'capable_generation_mu': float(row[3] or 0),
            'operational_capacity_mw': float(row[4] or 0),
            'coal_stock_days': float(row[5] or 0) if row[5] else None
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/filters/states', methods=['GET'])
def get_filter_states():
    """Get list of states for filtering"""
    try:
        query = text("""
            SELECT DISTINCT s.State_Code, s.State_Name
            FROM STATE s
            INNER JOIN POWERPLANTS p ON s.State_Code = p.State_Code
            ORDER BY s.State_Name
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'code': row[0],
            'name': row[1]
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/filters/sectors', methods=['GET'])
def get_filter_sectors():
    """Get list of sectors for filtering"""
    try:
        query = text("""
            SELECT DISTINCT sec.Sector_ID, sec.Sector_Name
            FROM SECTOR sec
            INNER JOIN POWERPLANTS p ON sec.Sector_ID = p.Sector_ID
            ORDER BY sec.Sector_Name
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'id': row[0],
            'name': row[1]
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/filters/types', methods=['GET'])
def get_filter_types():
    """Get list of energy types for filtering"""
    try:
        query = text("""
            SELECT DISTINCT et.Type_ID, et.Type_Name
            FROM ENERGYTYPE et
            INNER JOIN POWERPLANTS p ON et.Type_ID = p.Type_ID
            ORDER BY et.Type_Name
        """)
        
        results = db.session.execute(query).fetchall()
        
        data = [{
            'id': row[0],
            'name': row[1]
        } for row in results]
        
        return jsonify({'success': True, 'data': data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
