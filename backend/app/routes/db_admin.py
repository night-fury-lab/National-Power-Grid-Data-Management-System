from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import text
from datetime import datetime
import traceback
import subprocess
import os

bp = Blueprint('db_admin', __name__)


@bp.route('/generate-daily-report', methods=['GET'])
def generate_daily_report():
    """Generate a daily energy report for a given date (or today).
    This endpoint calls the sp_GenerateDailyEnergyReport stored procedure
    and returns the report as JSON. Expects query param 'report_date'.
    """
    try:
        # Accept report_date from either query param or JSON body.
        raw_report_date = request.args.get('report_date') or (request.json.get('report_date') if request.is_json else None)
        report_date = None
        
        if not raw_report_date:
            report_date = datetime.utcnow().date()
        else:
            # Be flexible with formats
            if isinstance(raw_report_date, (bytes, bytearray)):
                raw_report_date = raw_report_date.decode('utf-8')
            
            if isinstance(raw_report_date, str):
                parsed = None
                # Try YYYY-MM-DD first
                try:
                    parsed = datetime.strptime(raw_report_date, '%Y-%m-%d')
                except Exception:
                    # Try DD-MM-YYYY (from screenshot)
                    try:
                        parsed = datetime.strptime(raw_report_date, '%d-%m-%Y')
                    except Exception:
                        # Try ISO format (strip trailing Z if present)
                        try:
                            iso_str = raw_report_date.rstrip('Z')
                            parsed = datetime.fromisoformat(iso_str)
                        except Exception:
                            parsed = None

                if parsed is None:
                    return jsonify({'success': False, 'error': "report_date must be in 'YYYY-MM-DD', 'DD-MM-YYYY', or ISO format"}), 400

                report_date = parsed.date()
            elif isinstance(raw_report_date, datetime):
                report_date = raw_report_date.date()
            else:
                return jsonify({'success': False, 'error': 'report_date has unsupported type'}), 400

        # --- Logic now only calls the stored procedure ---
        try:
            # CALL stored procedure; some DB drivers return a proxy supporting fetchall()
            proc = db.session.execute(text("CALL sp_GenerateDailyEnergyReport(:d)"), {'d': report_date})
            try:
                rows = proc.fetchall()
            except Exception:
                # fallback to cursor
                cur = getattr(proc, 'cursor', None)
                rows = cur.fetchall() if cur is not None else []

            data = []
            for r in rows:
                # Stored procedure returns: State_Code, Report_Date, total_generated_mu, total_demand_mu, total_surplus_mu, total_imported_mu
                data.append({
                    'state_code': r[0],
                    'report_date': str(r[1]),
                    'total_generated_mu': float(r[2] or 0),
                    'total_demand_mu': float(r[3] or 0),
                    'total_surplus_mu': float(r[4] or 0),
                    'total_imported_mu': float(r[5] or 0)
                })

            return jsonify({'success': True, 'report_date': str(report_date), 'data': data}), 200
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error calling stored procedure: {e}\n{tb}")
            return jsonify({'success': False, 'error': str(e)}), 500
        
        # --- The second query (SELECT FROM REGION_DETAILS) has been removed ---

    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error generating daily report: {e}\n{tb}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/identify-underperforming', methods=['GET'])
def identify_underperforming():
    """Identify underperforming plants over the last N days with a threshold.
    Query params: threshold (default 60), days (default 30)
    """
    try:
        threshold = float(request.args.get('threshold', 60))
        days = int(request.args.get('days', 30))

        proc = db.session.execute(text("CALL sp_IdentifyUnderperformingPlants(:threshold, :days)"), {'threshold': threshold, 'days': days})
        results = proc.fetchall()

        data = [{
            'plant_id': r[0],
            'plant_name': r[1],
            'state_name': r[2],
            'avg_efficiency': float(r[3] or 0)
        } for r in results]

        return jsonify({'success': True, 'data': data}), 200
    except Exception as e:
        print(f"Error identifying underperforming plants: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/calculate-regional-metrics', methods=['GET'])
def calculate_regional_metrics():
    """Calculate regional metrics over a date range. Query params: start_date, end_date (YYYY-MM-DD)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not start_date or not end_date:
            return jsonify({'success': False, 'error': 'start_date and end_date are required'}), 400

        # Parse and validate date format (expecting YYYY-MM-DD)
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').date()
            ed = datetime.strptime(end_date, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'success': False, 'error': 'start_date and end_date must be in YYYY-MM-DD format'}), 400

        if sd > ed:
            return jsonify({'success': False, 'error': 'start_date must be before or equal to end_date'}), 400

        # Call stored procedure with date parameters
        proc = db.session.execute(text("CALL sp_CalculateRegionalMetrics(:start_date, :end_date)"), {'start_date': sd, 'end_date': ed})
        # Some DB drivers return a ResultProxy that supports fetchall(); others may require accessing cursor
        try:
            results = proc.fetchall()
        except Exception:
            # Try to access the raw cursor
            cur = proc.cursor if hasattr(proc, 'cursor') else None
            if cur is not None:
                results = cur.fetchall()
            else:
                results = []

        data = []
        for r in results:
            # Stored proc returns: Region, Total_Plants, Total_Generated_MU, Total_Demand_MU
            region = r[0]
            total_plants = r[1]
            # Convert to float and round to 2 decimals to avoid floating point imprecision
            total_generated = round(float(r[2] or 0), 2)
            total_demand = round(float(r[3] or 0), 2)
            data.append({
                'region': region,
                'total_plants': total_plants,
                'total_generated_mu': total_generated,
                'total_demand_mu': total_demand
            })

        return jsonify({'success': True, 'start_date': str(sd), 'end_date': str(ed), 'data': data}), 200
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error calculating regional metrics: {e}\n{tb}")
        # Return a concise message but log the full traceback on server
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/run-data-update', methods=['POST'])
def run_data_update():
    """Run the complete data update pipeline:
    1. integrated_web_scrapping.py
    2. parseall1.py
    3. parseall2.py
    4. parseall3.py
    5. SQL updates and stored procedures
    """
    try:
        # Get the base directory (DBMS_Final folder)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        
        # Get Python executable from config
        from app.config import Config
        python_exe = getattr(Config, 'PYTHON_EXECUTABLE', 'python')
        
        results = []
        
        # Step 1: Run integrated_web_scrapping.py
        print("Step 1: Running integrated_web_scrapping.py...")
        script1 = os.path.join(base_dir, 'integrated_web_scrapping.py')
        try:
            result = subprocess.run(
                [python_exe, script1],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=1500,  # 25 minutes timeout
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}  # Fix Unicode encoding
            )
            results.append({
                'step': 'Web Scraping',
                'success': result.returncode == 0,
                'output': result.stdout[-500:] if result.stdout else '',  # Last 500 chars
                'error': result.stderr[-500:] if result.stderr else ''
            })
            if result.returncode != 0:
                print(f"Web scraping failed: {result.stderr}")
        except Exception as e:
            results.append({'step': 'Web Scraping', 'success': False, 'error': str(e)})
            print(f"Web scraping error: {e}")
        
        # Step 2: Run parseall1.py
        print("Step 2: Running parseall1.py...")
        script2 = os.path.join(base_dir, 'parseall1.py')
        try:
            result = subprocess.run(
                [python_exe, script2],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=1500,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            results.append({
                'step': 'Parse Phase 1',
                'success': result.returncode == 0,
                'output': result.stdout[-500:] if result.stdout else '',
                'error': result.stderr[-500:] if result.stderr else ''
            })
            if result.returncode != 0:
                print(f"Parse 1 failed: {result.stderr}")
        except Exception as e:
            results.append({'step': 'Parse Phase 1', 'success': False, 'error': str(e)})
            print(f"Parse 1 error: {e}")
        
        # Step 3: Run parseall2.py
        print("Step 3: Running parseall2.py...")
        script3 = os.path.join(base_dir, 'parseall2.py')
        try:
            result = subprocess.run(
                [python_exe, script3],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=1500,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            results.append({
                'step': 'Parse Phase 2',
                'success': result.returncode == 0,
                'output': result.stdout[-500:] if result.stdout else '',
                'error': result.stderr[-500:] if result.stderr else ''
            })
            if result.returncode != 0:
                print(f"Parse 2 failed: {result.stderr}")
        except Exception as e:
            results.append({'step': 'Parse Phase 2', 'success': False, 'error': str(e)})
            print(f"Parse 2 error: {e}")
        
        # Step 4: Run parseall3.py
        print("Step 4: Running parseall3.py...")
        script4 = os.path.join(base_dir, 'parseall3.py')
        try:
            result = subprocess.run(
                [python_exe, script4],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=1500,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            results.append({
                'step': 'Parse Phase 3',
                'success': result.returncode == 0,
                'output': result.stdout[-500:] if result.stdout else '',
                'error': result.stderr[-500:] if result.stderr else ''
            })
            if result.returncode != 0:
                print(f"Parse 3 failed: {result.stderr}")
        except Exception as e:
            results.append({'step': 'Parse Phase 3', 'success': False, 'error': str(e)})
            print(f"Parse 3 error: {e}")
        
        # Step 5: Run SQL updates
        print("Step 5: Running SQL updates...")
        sql_results = []
        
        try:
            # Update Grid Frequency
            db.session.execute(text("UPDATE REGION_DETAILS SET Grid_Frequency_Hz = 60.00"))
            db.session.commit()
            sql_results.append({'query': 'UPDATE REGION_DETAILS', 'success': True})
        except Exception as e:
            db.session.rollback()
            sql_results.append({'query': 'UPDATE REGION_DETAILS', 'success': False, 'error': str(e)})
            print(f"Update REGION_DETAILS error: {e}")
        
        # Call stored procedures
        procedures = [
            'sp_UpdateRegionGenerationFromProduction',
            'sp_UpdateRegionSurplusAndImports',
            'sp_CalculatePlantEfficiency',
            'sp_InsertAllMissingActiveStatuses'
        ]
        
        for proc_name in procedures:
            try:
                db.session.execute(text(f"CALL {proc_name}()"))
                db.session.commit()
                sql_results.append({'procedure': proc_name, 'success': True})
                print(f"Successfully called {proc_name}")
            except Exception as e:
                db.session.rollback()
                sql_results.append({'procedure': proc_name, 'success': False, 'error': str(e)})
                print(f"Error calling {proc_name}: {e}")
        
        results.append({
            'step': 'Database Updates',
            'success': all(r.get('success', False) for r in sql_results),
            'details': sql_results
        })
        
        # Determine overall success
        overall_success = all(r.get('success', False) for r in results)
        
        return jsonify({
            'success': overall_success,
            'message': f"Pipeline completed. {sum(1 for r in results if r.get('success'))} of {len(results)} steps succeeded.",
            'results': results
        }), 200
        
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error in run_data_update: {e}\n{tb}")
        return jsonify({'success': False, 'error': str(e)}), 500
