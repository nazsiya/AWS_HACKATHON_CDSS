import boto3

def get_latest_stream_logs():
    client = boto3.client('logs', region_name='ap-south-1')
    log_group = '/aws/lambda/cdss-api-dev'
    
    try:
        response = client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        if not response['logStreams']:
            print("No log streams found.")
            return
            
        stream_name = response['logStreams'][0]['logStreamName']
        print(f"Latest stream: {stream_name}")
        
        response = client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            limit=20,
            startFromHead=False
        )
        
        for event in response['events']:
            print(event['message'].strip())
            
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    get_latest_stream_logs()
