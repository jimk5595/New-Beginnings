from models import PipelineRequest
from pipeline import run_pipeline

if __name__ == "__main__":
    request = PipelineRequest(
        model="gemini-3.0-flash",
        prompt="Test the pipeline"
    )
    response = run_pipeline(request)
    print(response.output)
