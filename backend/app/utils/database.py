from app import db
from sqlalchemy import text

class DatabaseHelper:
    
    @staticmethod
    def execute_query(query, params=None):
        """Execute a raw SQL query"""
        try:
            if params:
                result = db.session.execute(text(query), params)
            else:
                result = db.session.execute(text(query))
            
            return result.fetchall()
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def execute_procedure(procedure_name, params=None):
        """Execute a stored procedure"""
        try:
            if params:
                query = f"CALL {procedure_name}({','.join([':' + p for p in params.keys()])})"
                result = db.session.execute(text(query), params)
            else:
                query = f"CALL {procedure_name}()"
                result = db.session.execute(text(query))
            
            db.session.commit()
            return result.fetchall()
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def call_function(function_name, params):
        """Call a user-defined function"""
        try:
            param_string = ','.join([f":{p}" for p in params.keys()])
            query = f"SELECT {function_name}({param_string})"
            result = db.session.execute(text(query), params)
            
            return result.scalar()
        except Exception as e:
            raise e
    
    @staticmethod
    def test_connection():
        """Test database connection"""
        try:
            db.session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def get_table_count(table_name):
        """Get row count of a table"""
        try:
            query = f"SELECT COUNT(*) FROM {table_name}"
            result = db.session.execute(text(query))
            return result.scalar()
        except Exception as e:
            raise e
    