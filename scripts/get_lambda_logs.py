import boto3
from datetime import datetime, timezone, timedelta

def get_logs():
    client = boto3.client('logs', region_name='ap-south-1')
    log_group = '/aws/lambda/cdss-dev-gateway-get-hospitals'
    
    start_time = int((datetime.now(timezone.utc) - timedelta(minutes=15)).timestamp() * 1000)
    
    try:
        response = client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            filterPattern='FATAL'
        )
        for e in response.get('events', []):
            print(f"[{datetime.fromtimestamp(e['timestamp']/1000).isoformat()}] {e['message'].strip()}")
            
        print("--- All Warnings ---")
        response = client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            filterPattern='WARNING'
        )
        for e in response.get('events', []):
            print(f"[{datetime.fromtimestamp(e['timestamp']/1000).isoformat()}] {e['message'].strip()}")

    except Exception as e:
        print(f"Error fetching logs: {e}")

if __name__ == "__main__":
    get_logs()
