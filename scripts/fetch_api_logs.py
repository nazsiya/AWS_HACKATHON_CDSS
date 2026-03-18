import boto3
from datetime import datetime, timedelta

def get_latest_errors():
    client = boto3.client('logs', region_name='ap-south-1')
    log_group = '/aws/lambda/cdss-api-dev'
    
    start_time = int((datetime.utcnow() - timedelta(minutes=5)).timestamp() * 1000)
    
    try:
        response = client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            filterPattern='ERROR'
        )
        events = response.get('events', [])
        if not events:
            print("No new ERROR logs found. Searching without filterPattern to find traceback...")
            response = client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time
            )
            events = response.get('events', [])
            tracebacks = [e['message'] for e in events if 'Traceback' in e['message'] or 'Error' in e['message']]
            if tracebacks:
                for t in tracebacks[-3:]:
                    print(t)
            else:
                print("No tracebacks found at all in the last 5 minutes.")
        else:
            for event in events[-3:]:
                print(f"[{datetime.fromtimestamp(event['timestamp']/1000)}] {event['message']}")
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    get_latest_errors()
