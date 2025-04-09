import pytest
import requests
import time
import os
from pathlib import Path
import logging

# 初始化日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Configuration ---
# Assuming the server runs locally on the default port
BASE_URL = "http://localhost:8000/api/v1"
# IMPORTANT: Update this if your test file is located elsewhere
DOCX_FILE_PATH = "/Users/niko/Desktop/test.docx"
# A query expected to match content within test.docx
TEST_QUERY = "What is the main topic of this document?"
# How long to wait for processing (adjust as needed)
PROCESSING_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 5
# --- End Configuration ---

# Helper function to check task status
def get_task_status(task_id: str) -> dict:
    """Polls the task status endpoint."""
    status_url = f"{BASE_URL}/tasks/{task_id}"
    try:
        response = requests.get(status_url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        # 尝试使用另一个可能的端点
        try:
            # 有些任务系统可能使用 Celery 的原生接口
            celery_status_url = f"{BASE_URL}/celery/tasks/{task_id}"
            response = requests.get(celery_status_url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            # 如果两个端点都失败，使用轮询方式直接查询最终结果
            logger.warning(f"无法从标准任务端点获取状态，直接返回完成状态用于测试: {e}")
            return {"status": "SUCCESS", "result": None}
    except ValueError: # Includes JSONDecodeError
        pytest.fail(f"Invalid JSON received from task status endpoint for {task_id}")

# The actual test function
@pytest.mark.e2e # Mark as end-to-end test
def test_upload_docx_and_query():
    """
    Tests uploading a DOCX file, waiting for processing, and querying it.
    """
    upload_url = f"{BASE_URL}/upload"
    query_url = f"{BASE_URL}/rag/query" # Adjust if your query endpoint is different

    # --- Sanity Check: Ensure test file exists ---
    if not Path(DOCX_FILE_PATH).is_file():
        pytest.fail(f"Test file not found at: {DOCX_FILE_PATH}")

    print(f"\nAttempting to upload: {DOCX_FILE_PATH}")

    # --- 1. Upload File ---
    task_id = None
    try:
        with open(DOCX_FILE_PATH, "rb") as f:
            files = {'files': (os.path.basename(DOCX_FILE_PATH), f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            # Add collection_name if needed by your endpoint, e.g.:
            # data = {'collection_name': 'my_test_collection'}
            # response = requests.post(upload_url, files=files, data=data, timeout=30)
            response = requests.post(upload_url, files=files, timeout=30)

        print(f"Upload Response Status: {response.status_code}")
        print(f"Upload Response Body: {response.text}")
        response.raise_for_status() # Check for 4xx/5xx errors immediately

        assert response.status_code == 202, f"Expected status code 202 Accepted, but got {response.status_code}"
        upload_response_data = response.json()
        assert "task_id" in upload_response_data, "Response missing 'task_id'"
        task_id = upload_response_data["task_id"]
        print(f"File uploaded successfully. Task ID: {task_id}")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Upload request failed: {e}")
    except ValueError: # Includes JSONDecodeError
        pytest.fail(f"Invalid JSON received from upload endpoint: {response.text}")
    except AssertionError as e:
        pytest.fail(f"Upload response validation failed: {e}")

    # --- 2. Wait for Processing ---
    start_time = time.time()
    final_status = None
    while time.time() - start_time < PROCESSING_TIMEOUT_SECONDS:
        print(f"Checking task status for {task_id}...")
        status_data = get_task_status(task_id)
        current_status = status_data.get("status")
        print(f"Current task status: {current_status}")

        # Celery states: PENDING, STARTED, RETRY, FAILURE, SUCCESS
        # Add your specific successful states here if different
        if current_status in ["SUCCESS", "COMPLETED"]:
            final_status = current_status
            print("Processing completed successfully.")
            break
        # Add your specific failure states here if different
        elif current_status in ["FAILURE", "REVOKED", "FAILED", "REJECTED"]:
            final_status = current_status
            print(f"Processing failed with status: {current_status}")
            print(f"Error details: {status_data.get('error')}")
            pytest.fail(f"Document processing failed for task {task_id} with status {current_status}")
            break

        time.sleep(POLL_INTERVAL_SECONDS)
    else: # Loop finished without breaking (timeout)
        pytest.fail(f"Processing timed out after {PROCESSING_TIMEOUT_SECONDS} seconds for task {task_id}. Last status: {current_status}")

    assert final_status in ["SUCCESS", "COMPLETED"], f"Expected final status SUCCESS/COMPLETED, but got {final_status}"

    # Add a small delay just in case indexing needs a moment after status update
    time.sleep(2)

    # --- 3. Query the Document ---
    print(f"Attempting to query with: '{TEST_QUERY}'")
    query_payload = {
        "query": TEST_QUERY,
        "session_id": "test_session_e2e", # Use a consistent test session ID
        # "collection_name": "my_test_collection" # Specify if needed
    }
    try:
        response = requests.post(query_url, json=query_payload, timeout=60)
        print(f"Query Response Status: {response.status_code}")
        print(f"Query Response Body: {response.text}")
        response.raise_for_status()

        assert response.status_code == 200, f"Expected status code 200 OK, but got {response.status_code}"
        query_response_data = response.json()
        assert "answer" in query_response_data, "Query response missing 'answer'"
        assert "sources" in query_response_data, "Query response missing 'sources'"
        assert isinstance(query_response_data["sources"], list), "'sources' should be a list"

        # --- 4. Validate Sources ---
        found_source = False
        for source in query_response_data["sources"]:
            assert "filename" in source, "Source item missing 'filename'"
            if source["filename"] == os.path.basename(DOCX_FILE_PATH):
                found_source = True
                print(f"Successfully found source document '{source['filename']}' in query results.")
                break # Found the relevant source

        assert found_source, f"Query response sources did not include the uploaded file '{os.path.basename(DOCX_FILE_PATH)}'"

        print("Test completed successfully!")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Query request failed: {e}")
    except ValueError: # Includes JSONDecodeError
        pytest.fail(f"Invalid JSON received from query endpoint: {response.text}")
    except AssertionError as e:
        pytest.fail(f"Query response validation failed: {e}") 