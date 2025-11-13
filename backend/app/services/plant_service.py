from app import db
from app.models import PowerPlant, ProductionLog, OperationalStatus
from app.schemas import powerplant_schema, powerplants_schema
from sqlalchemy import text
from datetime import datetime, timedelta

class PlantService:
    
    @staticmethod
    def get_all_plants(page=1, per_page=20, filters=None):
        """Get all plants with pagination and filters"""
        query = PowerPlant.query
        
        if filters:
            if filters.get('state_code'):
                query = query.filter(PowerPlant.State_Code == filters['state_code'])
            if filters.get('energy_type'):
                query = query.filter(PowerPlant.Type_ID == filters['energy_type'])
            if filters.get('sector'):
                query = query.filter(PowerPlant.Sector_ID == filters['sector'])
            if filters.get('search'):
                query = query.filter(PowerPlant.Plant_Name.like(f"%{filters['search']}%"))
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'plants': powerplants_schema.dump(paginated.items),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages
            }
        }
    
    @staticmethod
    def get_plant_by_id(plant_id):
        """Get detailed plant information"""
        query = text("""
            SELECT 
                p.Plant_ID,
                p.Plant_Name,
                s.State_Name,
                s.Region,
                sec.Sector_Name,
                et.Type_Name,
                et.Description,
                ROUND(AVG(pl.Efficiency_Percentage), 2) AS Avg_Efficiency,
                ROUND(SUM(pl.Todays_Actual_MU), 2) AS Total_Generation_MU,
                ROUND(AVG(pl.Operational_Capacity_MW), 2) AS Avg_Capacity_MW,
                MAX(pl.Log_Date) AS Last_Log_Date,
                (SELECT Status FROM OPERATIONAL_STATUS 
                 WHERE Plant_ID = p.Plant_ID 
                 ORDER BY Status_Date DESC LIMIT 1) AS Current_Status
            FROM POWERPLANTS p
            INNER JOIN STATE s ON p.State_Code = s.State_Code
            INNER JOIN SECTOR sec ON p.Sector_ID = sec.Sector_ID
            INNER JOIN ENERGYTYPE et ON p.Type_ID = et.Type_ID
            LEFT JOIN PRODUCTIONLOG pl ON p.Plant_ID = pl.Plant_ID
            WHERE p.Plant_ID = :plant_id
            GROUP BY p.Plant_ID, p.Plant_Name, s.State_Name, s.Region, 
                     sec.Sector_Name, et.Type_Name, et.Description
        """)
        
        result = db.session.execute(query, {'plant_id': plant_id}).fetchone()
        
        if not result:
            return None
        
        return {
            'plant_id': result[0],
            'plant_name': result[1],
            'state_name': result[2],
            'region': result[3],
            'sector_name': result[4],
            'energy_type': result[5],
            'description': result[6],
            'avg_efficiency': float(result[7] or 0),
            'total_generation_mu': float(result[8] or 0),
            'avg_capacity_mw': float(result[9] or 0),
            'last_log_date': str(result[10]) if result[10] else None,
            'current_status': result[11]
        }
    
    @staticmethod
    def create_plant(data):
        """Create a new plant"""
        new_plant = PowerPlant(
            Plant_ID=data['plant_id'],
            Plant_Name=data['plant_name'],
            State_Code=data['state_code'],
            Sector_ID=data['sector_id'],
            Type_ID=data['type_id']
        )
        
        db.session.add(new_plant)
        db.session.commit()
        
        return powerplant_schema.dump(new_plant)
    
    @staticmethod
    def update_plant(plant_id, data):
        """Update existing plant"""
        plant = PowerPlant.query.get(plant_id)
        
        if not plant:
            return None
        
        if 'plant_name' in data:
            plant.Plant_Name = data['plant_name']
        if 'state_code' in data:
            plant.State_Code = data['state_code']
        if 'sector_id' in data:
            plant.Sector_ID = data['sector_id']
        if 'type_id' in data:
            plant.Type_ID = data['type_id']
        
        db.session.commit()
        
        return powerplant_schema.dump(plant)
    
    @staticmethod
    def delete_plant(plant_id):
        """Delete a plant"""
        plant = PowerPlant.query.get(plant_id)
        
        if not plant:
            return False
        
        db.session.delete(plant)
        db.session.commit()
        
        return True
    
    @staticmethod
    def get_production_history(plant_id, days=30):
        """Get production history for a plant"""
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
        
        result = db.session.execute(query, {'plant_id': plant_id, 'days': days})
        
        return [{
            'date': str(row[0]),
            'efficiency': float(row[1] or 0),
            'actual_mu': float(row[2] or 0),
            'capable_mu': float(row[3] or 0),
            'capacity_mw': float(row[4] or 0),
            'coal_stock_days': float(row[5] or 0) if row[5] else None
        } for row in result]
