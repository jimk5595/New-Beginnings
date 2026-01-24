interface PipelineRequest {
    model: string;
    prompt: string;
    task_type?: string;
}

interface PipelineResponse {
    output: string;
}

export async function runEliza(request: PipelineRequest): Promise<PipelineResponse> {
    const response = await fetch("/run_eliza", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request)
    });
    return response.json();
}
