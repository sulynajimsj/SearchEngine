# deploy.py
import boto3
from config import AWS_ACCESS_KEY, AWS_SECRET_KEY, GROUP_NUMBER

def setup_aws():
    # Connect to AWS
    print("Connecting to AWS...")
    ec2 = boto3.client(
        'ec2',
        region_name='us-east-1',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    return ec2

def create_key_pair(ec2):
    # Create key for SSH access
    print("Creating key pair...")
    key_name = f'ece326-group{GROUP_NUMBER}-key'
    try:
        # Delete existing key pair if it exists
        try:
            ec2.delete_key_pair(KeyName=key_name)
            print(f"Deleted existing key pair: {key_name}")
        except:
            pass
        
        key = ec2.create_key_pair(KeyName=key_name)
        # Save private key
        with open(f'{key_name}.pem', 'w') as file:
            file.write(key['KeyMaterial'])
        # Set correct permissions
        import os
        os.chmod(f'{key_name}.pem', 0o400)
        print(f"Created key pair: {key_name}")
        return key_name
    except Exception as e:
        print(f"Error creating key pair: {e}")
        return None

def create_security_group(ec2):
    # Create security group
    print("Creating security group...")
    group_name = f'ece326-group{GROUP_NUMBER}'
    try:
        group = ec2.create_security_group(
            GroupName=group_name,
            Description='ECE326 Lab2 Security Group'
        )
        
        # Add firewall rules
        ec2.authorize_security_group_ingress(
            GroupId=group['GroupId'],
            IpPermissions=[
                # SSH
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # HTTP
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # Ping
                {
                    'IpProtocol': 'icmp',
                    'FromPort': -1,
                    'ToPort': -1,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        print(f"Created security group: {group_name}")
        return group['GroupId']
    except Exception as e:
        print(f"Error creating security group: {e}")
        return None
    
def allocate_elastic_ip(ec2, instance_id):
    try:
        # Allocate elastic IP
        allocation = ec2.allocate_address(Domain='vpc')
        elastic_ip = allocation['PublicIp']
        allocation_id = allocation['AllocationId']
        
        # Associate elastic IP with instance
        ec2.associate_address(
            AllocationId=allocation_id,
            InstanceId=instance_id
        )
        
        print(f"Allocated and associated elastic IP: {elastic_ip}")
        return elastic_ip
    except Exception as e:
        print(f"Error allocating elastic IP: {e}")
        return None

def launch_instance(ec2, key_name, security_group_id):
    # Launch EC2 instance
    print("Launching EC2 instance...")
    try:
        instance = ec2.run_instances(
            ImageId='ami-0c7217cdde317cfec',  # Ubuntu 22.04 LTS
            InstanceType='t2.micro',
            KeyName=key_name,
            SecurityGroupIds=[security_group_id],
            MinCount=1,
            MaxCount=1
        )
        instance_id = instance['Instances'][0]['InstanceId']
        
        # Wait for instance to be running
        print("Waiting for instance to start...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Get instance information
        instance_info = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = instance_info['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        return instance_id, public_ip
    except Exception as e:
        print(f"Error launching instance: {e}")
        return None, None

def main():
    print("Starting AWS deployment...")
    
    # Setup AWS connection
    ec2 = setup_aws()
    
    # Create key pair
    key_name = create_key_pair(ec2)
    if not key_name:
        return
    
    # Create security group
    security_group_id = create_security_group(ec2)
    if not security_group_id:
        return
    
    # Launch instance
    instance_id, public_ip = launch_instance(ec2, key_name, security_group_id)
    if not instance_id:
        return
    
    elastic_ip = allocate_elastic_ip(ec2, instance_id)
    if not elastic_ip:
        return
    
    print("Deployment completed successfully!")

    print(f"""
    Deployment completed successfully!
    Instance ID: {instance_id}
    Original Public IP: {public_ip}
    Elastic IP: {elastic_ip}
    
    To connect to your instance:
    ssh -i {key_name}.pem ubuntu@{elastic_ip}
    
    To copy files to your instance:
    scp -i {key_name}.pem <local-file> ubuntu@{elastic_ip}:~/<remote-path>
    """)

if __name__ == "__main__":
    main()