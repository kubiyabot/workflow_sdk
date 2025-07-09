from kubiya_workflow_sdk.dsl_experimental import *


def create_volume_file_sharing_workflow() -> Workflow:
    """Create a workflow with two tools that share data through a volume"""

    # Step 1: Write to file tool
    write_to_file_step = ExecutorStep(
        name="write-to-file",
        description="First tool writes data to a file in a shared volume",
        output="WRITE_RESULT",
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="file-writer",
                    description="Writes sample data to a file in the shared volume",
                    type="docker",
                    image="python:3.12-slim-bullseye",
                    with_volumes=[{"path": "/shared", "name": "shared-data"}],
                    args=[
                        ArgDefinition(
                            name="message",
                            type="string",
                            required=True,
                            default="Hello from the writer tool!",
                        ),
                        ArgDefinition(
                            name="filename",
                            type="string",
                            required=True,
                            default="shared_data.txt",
                        ),
                    ],
                    with_files=[
                        FileDefinition(
                            destination="/tmp/writer.py",
                            content="""#!/usr/bin/env python3
import os
import json
import datetime

# Get arguments from environment
message = os.environ.get('message', 'Hello from the writer tool!')
filename = os.environ.get('filename', 'shared_data.txt')

# Create data to write
data = {
    'message': message,
    'timestamp': datetime.datetime.now().isoformat(),
    'writer': 'file-writer-tool',
    'additional_data': {
        'numbers': [1, 2, 3, 4, 5],
        'status': 'success'
    }
}

# Write to the shared volume
file_path = f'/shared/{filename}'
with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f'Successfully wrote data to {file_path}')
print(f'Data written: {json.dumps(data, indent=2)}')

# Also create a simple text file
with open('/shared/simple.txt', 'w') as f:
    f.write(f'{message}\\nWritten at: {datetime.datetime.now()}\\n')

print('Files created in /shared volume:')
os.system('ls -la /shared/')""",
                        )
                    ],
                    content="set -e\npython /tmp/writer.py",
                ),
                args={
                    "message": "Data from step 1 - processing pipeline started!",
                    "filename": "pipeline_data.json",
                },
            ),
        ),
    )

    # Step 2: Read from file tool
    read_from_file_step = ExecutorStep(
        name="read-from-file",
        description="Second tool reads the data from the file written by the first tool",
        output="READ_RESULT",
        depends=["write-to-file"],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="file-reader",
                    description="Reads and processes data from the shared volume file",
                    type="docker",
                    image="python:3.12-slim-bullseye",
                    with_volumes=[{"path": "/shared", "name": "shared-data"}],
                    args=[
                        ArgDefinition(
                            name="filename",
                            type="string",
                            required=True,
                            default="shared_data.txt",
                        ),
                        ArgDefinition(
                            name="process_numbers",
                            type="boolean",
                            required=False,
                            default="true",
                        ),
                    ],
                    with_files=[
                        FileDefinition(
                            destination="/tmp/reader.py",
                            content="""#!/usr/bin/env python3
import os
import json

# Get arguments from environment
filename = os.environ.get('filename', 'shared_data.txt')
process_numbers = os.environ.get('process_numbers', 'true').lower() == 'true'

print('Files available in /shared volume:')
os.system('ls -la /shared/')

# Read the JSON file
file_path = f'/shared/{filename}'
try:
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    print(f'Successfully read data from {file_path}')
    print(f'Original data: {json.dumps(data, indent=2)}')
    
    # Process the data
    processed_data = {
        'original_message': data.get('message', ''),
        'original_timestamp': data.get('timestamp', ''),
        'reader_timestamp': __import__('datetime').datetime.now().isoformat(),
        'reader': 'file-reader-tool',
        'processing_result': {}
    }
    
    # Process numbers if requested and available
    if process_numbers and 'additional_data' in data and 'numbers' in data['additional_data']:
        numbers = data['additional_data']['numbers']
        processed_data['processing_result'] = {
            'original_numbers': numbers,
            'sum': sum(numbers),
            'max': max(numbers),
            'min': min(numbers),
            'count': len(numbers),
            'doubled': [n * 2 for n in numbers]
        }
    
    print(f'Processed result: {json.dumps(processed_data, indent=2)}')
    
    # Also read the simple text file if it exists
    simple_file_path = '/shared/simple.txt'
    if os.path.exists(simple_file_path):
        with open(simple_file_path, 'r') as f:
            simple_content = f.read()
        print(f'Simple text file content:\\n{simple_content}')
    
    # Write processed result back to volume for potential next steps
    with open('/shared/processed_result.json', 'w') as f:
        json.dump(processed_data, f, indent=2)
    
    print('Processing completed successfully!')
    
except FileNotFoundError:
    print(f'Error: File {file_path} not found in shared volume')
    print('Available files:')
    os.system('ls -la /shared/')
except json.JSONDecodeError as e:
    print(f'Error: Failed to parse JSON from {file_path}: {e}')
except Exception as e:
    print(f'Error: {e}')""",
                        )
                    ],
                    content="set -e\npython /tmp/reader.py",
                ),
                args={
                    "filename": "pipeline_data.json",
                    "process_numbers": "true",
                },
            ),
        ),
    )

    # Create the complete workflow
    workflow = Workflow(
        name="volume-file-sharing-workflow",
        description="A workflow with two tools that share data through a volume - one writes to a file and another reads from it",
        steps=[
            write_to_file_step,
            read_from_file_step,
        ],
    )

    return workflow


if __name__ == "__main__":
    # Create and display the workflow
    workflow = create_volume_file_sharing_workflow()
    print("Volume File Sharing Workflow:")
    print(workflow.model_dump_json(indent=2, exclude_none=True))

    print("\nWorkflow created successfully!")
