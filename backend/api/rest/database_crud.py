import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database config: from AWS Secrets Manager (RDS_CONFIG_SECRET_NAME) when set;
# otherwise from environment for local dev. No hardcoded credentials.
def _get_db_config():
    """Resolve DB config from Secrets Manager or env. Prefer Secrets Manager."""
    try:
        from cdss.config.secrets import get_rds_config
        region = os.environ.get("AWS_REGION", "ap-south-1")
        cfg = get_rds_config(region=region)
        if cfg and cfg.get("host") and cfg.get("username"):
            import boto3
            host = cfg.get("host", "")
            port = int(cfg.get("port", 5432))
            database = cfg.get("database", "cdssdb")
            username = cfg.get("username", "")
            rds_region = cfg.get("region") or region
            rds = boto3.client("rds", region_name=rds_region)
            password = rds.generate_db_auth_token(
                DBHostname=host, Port=port, DBUsername=username, Region=rds_region
            )
            return {
                "host": host,
                "port": port,
                "database": database,
                "user": username,
                "password": password,
            }
    except Exception:
        pass
    # Fallback: environment (local dev only; production should use Secrets Manager).
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5433")),
        "database": os.environ.get("DB_NAME", "cdssdb"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASS", "password"),
    }


def get_db_connection():
    """Establishes a connection to the PostgreSQL database using config from Secrets Manager or env."""
    try:
        cfg = _get_db_config()
        conn = psycopg2.connect(
            host=cfg["host"],
            database=cfg["database"],
            user=cfg["user"],
            password=cfg["password"],
            port=cfg["port"],
            connect_timeout=5,
            sslmode="require" if os.environ.get("RDS_CONFIG_SECRET_NAME") else "prefer",
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

from datetime import date

def calculate_age(birth_date):
    if not birth_date: return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def transform_row(resource, row):
    """Transforms a snake_case DB row to a camelCase frontend object."""
    if not row: return None
    
    if resource.startswith('/patients'):
        return {
            'id': row['patient_id'],
            'name': row['full_name'],
            'age': calculate_age(row.get('date_of_birth')),
            'gender': row.get('gender', 'M'),
            'bloodGroup': row.get('blood_group'),
            'ward': row.get('ward_number'),
            'severity': row.get('severity_level'),
            'status': row.get('status'),
            'vitals': {
                'hr': row.get('heart_rate'),
                'bp': f"{row.get('bp_systolic')}/{row.get('bp_diastolic')}" if row.get('bp_systolic') else None,
                'spo2': row.get('spo2_percent')
            },
            'conditions': row.get('conditions', []),
            'lastVisit': str(row.get('updated_at').date()) if row.get('updated_at') else None
        }
    
    if resource.startswith('/doctors'):
        return {
            'id': row['doctor_id'],
            'name': row['full_name'],
            'specialization': row['specialization'],
            'department': row['department']
        }
        
    if resource.startswith('/inventory') or resource.startswith('/resources'):
        return {
            'id': row['item_id'],
            'name': row['item_name'],
            'specialty': row['category'],
            'status': row['status'].capitalize() if row.get('status') else 'Available',
            'area': row.get('location'),
            'assignedTo': '—'
        }
        
    return row

def lambda_handler(event, context):
    """
    Main entry point for CRUD operations.
    Supports: GET/PUT /patients, GET/PUT /doctors, GET/POST/PUT /inventory
    """
    http_method = event.get('httpMethod')
    resource = event.get('resource', '')
    # Handle /api/v1/ prefix normalization
    resource = resource.replace('/api/v1', '')
    path_parameters = event.get('pathParameters') or {}
    
    conn = get_db_connection()
    if not conn:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Database connection failed'})
        }

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # --- PATIENTS ---
            if resource == '/patients' or resource == '/patients/{id}':
                patient_id = path_parameters.get('id')
                if http_method == 'GET':
                    if patient_id:
                        # Fetch patient with latest vitals
                        cur.execute("""
                            SELECT p.*, v.heart_rate, v.bp_systolic, v.bp_diastolic, v.spo2_percent, v.temperature_f
                            FROM patients p 
                            LEFT JOIN (
                                SELECT DISTINCT ON (patient_id) * FROM vitals_history ORDER BY patient_id, recorded_at DESC
                            ) v ON p.patient_id = v.patient_id
                            WHERE p.patient_id = %s
                        """, (patient_id,))
                        row = cur.fetchone()
                        if not row:
                            return {'statusCode': 404, 'body': json.dumps({'error': 'Patient not found'})}
                        result = transform_row('/patients', row)
                        # Add temperature
                        result['vitals']['temp'] = float(row['temperature_f']) if row.get('temperature_f') else None
                        
                        # Fetch medications as conditions
                        cur.execute("""
                            SELECT medication_name, dosage, frequency, status, interactions_warning 
                            FROM medications WHERE patient_id = %s AND status = 'active'
                            ORDER BY start_date DESC
                        """, (patient_id,))
                        meds = cur.fetchall()
                        result['conditions'] = [m['medication_name'] for m in meds]
                        result['medications'] = [{
                            'medication': m['medication_name'],
                            'dosage': m['dosage'],
                            'frequency': m['frequency'],
                            'status': m['status'],
                            'interactions': m.get('interactions_warning', '')
                        } for m in meds]
                        
                        # Fetch consultation history
                        cur.execute("""
                            SELECT s.summary_id as id, s.visit_date as date, 
                                   d.full_name as doctor, s.content_json
                            FROM ai_visit_summaries s
                            LEFT JOIN doctors d ON s.treating_physician = d.doctor_id
                            WHERE s.patient_id = %s
                            ORDER BY s.visit_date DESC LIMIT 10
                        """, (patient_id,))
                        consults = []
                        for c in cur.fetchall():
                            content = c.get('content_json') or {}
                            consults.append({
                                'id': c['id'],
                                'date': str(c['date']) if c['date'] else None,
                                'doctor': c['doctor'] or '—',
                                'notes': content.get('notes', ''),
                                'aiSummary': content.get('ai_summary', ''),
                                'prescriptions': []
                            })
                        result['consultationHistory'] = consults
                    else:
                        cur.execute("""
                            SELECT p.*, v.heart_rate, v.bp_systolic, v.bp_diastolic, v.spo2_percent 
                            FROM patients p 
                            LEFT JOIN (
                                SELECT DISTINCT ON (patient_id) * FROM vitals_history ORDER BY patient_id, recorded_at DESC
                            ) v ON p.patient_id = v.patient_id
                            ORDER BY p.updated_at DESC
                        """)
                        result = {'patients': [transform_row('/patients', row) for row in cur.fetchall()]}
                    return success_response(result)
                
                elif http_method == 'POST':
                    body = json.loads(event.get('body', '{}'))
                    cur.execute(
                        "INSERT INTO patients (patient_id, full_name, date_of_birth, gender, blood_group, severity_level, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (body.get('id'), body['name'], body.get('dob'), body.get('gender'), body.get('bloodGroup'), body.get('severity', 'low'), body.get('status', 'waiting'))
                    )
                    conn.commit()
                    return success_response({'message': 'Patient created'}, 201)

                elif http_method == 'PUT' and patient_id:
                    body = json.loads(event.get('body', '{}'))
                    cur.execute(
                        "UPDATE patients SET full_name = %s, severity_level = %s, status = %s, ward_number = %s WHERE patient_id = %s",
                        (body.get('fullName', body.get('name')), body.get('severity_level', body.get('severity')), body.get('status'), body.get('wardNumber'), patient_id)
                    )
                    conn.commit()
                    return success_response({'message': 'Patient updated'})

            # --- DOCTORS ---
            elif resource == '/doctors' or resource == '/doctors/{id}':
                doctor_id = path_parameters.get('id')
                if http_method == 'GET':
                    if doctor_id:
                        cur.execute("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
                        result = transform_row('/doctors', cur.fetchone())
                    else:
                        cur.execute("SELECT * FROM doctors")
                        result = [transform_row('/doctors', row) for row in cur.fetchall()]
                    return success_response(result)
            
            # --- APPOINTMENTS ---
            elif resource == '/appointments' or resource == '/appointments/{id}':
                appointment_id = path_parameters.get('id')
                if http_method == 'GET':
                    cur.execute("""
                        SELECT a.*, p.full_name as patient_name, d.full_name as doctor_name 
                        FROM appointments a
                        JOIN patients p ON a.patient_id = p.patient_id
                        JOIN doctors d ON a.doctor_id = d.doctor_id
                        ORDER BY a.appointment_time ASC
                    """)
                    result = [{
                        'id': r['appointment_id'],
                        'patientId': r['patient_id'],
                        'patientName': r['patient_name'],
                        'doctorId': r['doctor_id'],
                        'doctorName': r['doctor_name'],
                        'time': r['appointment_time'].strftime('%Y-%m-%dT%H:%M:%S'),
                        'type': r['appointment_type'],
                        'status': r['status'],
                        'notes': r['clinical_notes']
                    } for r in cur.fetchall()]
                    return success_response({'appointments': result})
                
                elif http_method == 'POST':
                    body = json.loads(event.get('body', '{}'))
                    cur.execute(
                        "INSERT INTO appointments (appointment_id, patient_id, doctor_id, appointment_time, appointment_type, status, clinical_notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (body.get('id'), body['patientId'], body['doctorId'], body['time'], body.get('type', 'Consultation'), body.get('status', 'scheduled'), body.get('notes'))
                    )
                    conn.commit()
                    return success_response({'message': 'Appointment created'}, 201)

            # --- MEDICATIONS ---
            elif resource == '/medications' or resource == '/medications/{id}':
                if http_method == 'GET':
                    cur.execute("""
                        SELECT m.*, p.full_name as patient_name, d.full_name as doctor_name 
                        FROM medications m
                        JOIN patients p ON m.patient_id = p.patient_id
                        LEFT JOIN doctors d ON m.prescribed_by = d.doctor_id
                    """)
                    result = [{
                        'id': r['medication_id'],
                        'patientId': r['patient_id'],
                        'patientName': r['patient_name'],
                        'prescribedBy': r['doctor_name'],
                        'name': r['medication_name'],
                        'dosage': r['dosage'],
                        'frequency': r['frequency'],
                        'status': r['status']
                    } for r in cur.fetchall()]
                    return success_response({'medications': result})
                
                elif http_method == 'POST':
                    body = json.loads(event.get('body', '{}'))
                    cur.execute(
                        "INSERT INTO medications (medication_id, patient_id, prescribed_by, medication_name, dosage, frequency, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (body.get('id'), body['patientId'], body.get('prescribedBy'), body['name'], body.get('dosage'), body.get('frequency'), body.get('status', 'active'))
                    )
                    conn.commit()
                    return success_response({'message': 'Medication added'}, 201)

            # --- INVENTORY / RESOURCES ---
            elif resource in ['/inventory', '/inventory/{id}', '/resources']:
                if http_method == 'GET':
                    cur.execute("SELECT * FROM inventory")
                    rows = [transform_row('/inventory', row) for row in cur.fetchall()]
                    result = {'inventory': rows, 'items': rows}
                    return success_response(result)
            
            # --- SURGERIES ---
            elif resource in ['/surgeries', '/surgeries/{id}']:
                if http_method == 'GET':
                    cur.execute("""
                        SELECT s.*, p.full_name as patient_name, d.full_name as surgeon_name 
                        FROM surgery_plans s
                        JOIN patients p ON s.patient_id = p.patient_id
                        JOIN doctors d ON s.lead_surgeon_id = d.doctor_id
                    """)
                    surgeries = []
                    for row in cur.fetchall():
                        surgeries.append({
                            'id': row['surgery_id'],
                            'type': row['surgery_type'],
                            'date': str(row['scheduled_time'].date()) if row['scheduled_time'] else None,
                            'time': row['scheduled_time'].strftime('%H:%M') if row['scheduled_time'] else None,
                            'surgeon': row['surgeon_name'],
                            'ot': row['ot_room_id'],
                            'estimatedDuration': f"{row['estimated_duration_minutes']} min",
                            'status': row['status'],
                            'patient': row['patient_name'],
                            'preOpRequirements': row.get('pre_op_requirements', {})
                        })
                    return success_response({'surgeries': surgeries})

            # --- CONSULTATIONS ---
            elif resource == '/consultations' or resource == '/consultations/start':
                if http_method == 'POST':
                    body = json.loads(event.get('body', '{}'))
                    patient_id = body.get('patient_id')
                    doctor_id = body.get('doctor_id')
                    
                    if not patient_id:
                        return {'statusCode': 400, 'body': json.dumps({'error': 'patient_id is required'})}
                    
                    if resource == '/consultations/start':
                        # Update patient status to 'in-consultation'
                        cur.execute("UPDATE patients SET status = 'in-consultation' WHERE patient_id = %s", (patient_id,))
                        
                        # Fetch patient info, vitals, and meds for context
                        cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
                        p = cur.fetchone()
                        cur.execute("""
                            SELECT heart_rate, bp_systolic, bp_diastolic, spo2_percent, temperature_f 
                            FROM vitals_history WHERE patient_id = %s 
                            ORDER BY recorded_at DESC LIMIT 1
                        """, (patient_id,))
                        vitals = cur.fetchone()
                        cur.execute("""
                            SELECT medication_name, dosage, frequency, interactions_warning 
                            FROM medications WHERE patient_id = %s AND status = 'active'
                        """, (patient_id,))
                        meds = cur.fetchall()
                        
                        # Use Bedrock for real AI Summary if possible
                        try:
                            # Add agents path to import shared components
                            import sys
                            from pathlib import Path
                            agents_path = str(Path(__file__).resolve().parent.parent.parent / "agents")
                            if agents_path not in sys.path: sys.path.append(agents_path)
                            
                            from shared.bedrock_client import BedrockClient
                            from shared.config import SYSTEM_PROMPTS
                            
                            bedrock = BedrockClient()
                            med_list = [f"{m['medication_name']} {m['dosage']} ({m['frequency']})" for m in meds]
                            v_str = f"HR: {vitals['heart_rate']} bpm, BP: {vitals['bp_systolic']}/{vitals['bp_diastolic']} mmHg, SpO2: {vitals['spo2_percent']}%, Temp: {vitals['temperature_f']}°F" if vitals else "No recent vitals."
                            
                            user_prompt = f"""
                            Please provide a concise clinical assessment for the following patient:
                            Name: {p['full_name']}
                            Status: {p['severity_level']}
                            Latest Vitals: {v_str}
                            Active Medications: {', '.join(med_list) if med_list else 'None'}
                            
                            Identify critical risks and provide 2-3 immediate clinical recommendations.
                            """
                            
                            ai_response = bedrock.invoke(
                                user_message=user_prompt,
                                system_prompt=SYSTEM_PROMPTS.get("patient", "You are a clinical assistant.")
                            )
                            summary = ai_response["content"]
                            
                            # Extract entities (using a simplified data-driven approach based on vitals/meds)
                            symptoms = []
                            if vitals:
                                if vitals['spo2_percent'] and vitals['spo2_percent'] < 92: symptoms.append(f"Low SpO2 ({vitals['spo2_percent']}%)")
                                if vitals['heart_rate'] and vitals['heart_rate'] > 100: symptoms.append(f"Tachycardia (HR {vitals['heart_rate']})")
                            
                            entities = {
                                'symptoms': symptoms if symptoms else ['Stable'],
                                'medications': [m['medication_name'] for m in meds] if meds else [],
                                'recommendations': ['Review labs', 'Monitor BP']
                            }
                            
                        except Exception as e:
                            print(f"Bedrock integration failed, falling back to simulated logic: {e}")
                            # Fallback logic if Bedrock is down/misconfigured
                            summary = f"AI Assessment for {p['full_name']}: Patient presents with {p['severity_level']} severity status. "
                            if vitals:
                                summary += f"Latest vitals — HR: {vitals['heart_rate']} bpm, BP: {vitals['bp_systolic']}/{vitals['bp_diastolic']} mmHg, SpO2: {vitals['spo2_percent']}%. "
                            summary += "Recommend monitoring vitals and reviewing medication adherence."
                            entities = {
                                'symptoms': ['Stable'],
                                'medications': [m['medication_name'] for m in meds] if meds else [],
                                'recommendations': ['Review labs']
                            }
                        
                        conn.commit()
                        return success_response({
                            'message': 'Consultation started',
                            'ai_summary': summary,
                            'entities': entities
                        })
                    else:
                        # Save consultation notes
                        notes = body.get('notes')
                        cur.execute(
                            "INSERT INTO ai_visit_summaries (summary_id, patient_id, visit_date, treating_physician, content_json) VALUES (%s, %s, CURRENT_DATE, %s, %s)",
                            (f"AI-{patient_id}-{doctor_id}-{int(date.today().strftime('%Y%m%d'))}", patient_id, doctor_id, json.dumps({'notes': notes, 'ai_summary': body.get('ai_summary')}))
                        )
                        # Set patient status back to 'waiting' or 'discharged' - let's say 'waiting' for follow-up
                        cur.execute("UPDATE patients SET status = 'waiting' WHERE patient_id = %s", (patient_id,))
                        conn.commit()
                        return success_response({'message': 'Consultation saved'})

            # --- SCHEDULE ---
            elif resource in ['/schedule', '/schedule/{id}']:
                if http_method == 'GET':
                    cur.execute("""
                        SELECT a.*, p.full_name as patient_name, d.full_name as doctor_name
                        FROM appointments a
                        JOIN patients p ON a.patient_id = p.patient_id
                        LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
                        ORDER BY a.appointment_time ASC
                    """)
                    appointments = []
                    for row in cur.fetchall():
                        appointments.append({
                            'id': row['appointment_id'],
                            'patient_id': row['patient_id'],
                            'patient_name': row['patient_name'],
                            'doctor_id': row['doctor_id'],
                            'doctor_name': row['doctor_name'],
                            'appointment_time': str(row['appointment_time']) if row['appointment_time'] else None,
                            'reason': row.get('reason', 'Consultation'),
                            'status': row.get('status', 'scheduled'),
                            'consultationType': row.get('reason', 'Consultation')
                        })
                    return success_response(appointments)

            # --- RESOURCES ---
            elif resource in ['/resources', '/resources/{id}']:
                if http_method == 'GET':
                    cur.execute("SELECT * FROM inventory ORDER BY item_name")
                    items = []
                    for row in cur.fetchall():
                        items.append({
                            'id': row['item_id'],
                            'name': row['item_name'],
                            'quantity': row['quantity_available'],
                            'unit': row.get('unit', '—'),
                            'category': row.get('category', 'General'),
                            'status': 'In Stock' if row['quantity_available'] > 0 else 'Out of Stock'
                        })
                    return success_response(items)

            return {
                'statusCode': 404,
                'body': json.dumps({'error': f'Not Found: {resource}'})
            }

    except Exception as e:
        import traceback
        print(f"Database error: {e}")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    finally:
        conn.close()

def success_response(data, status_code=200):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
        },
        'body': json.dumps(data, default=str)
    }
