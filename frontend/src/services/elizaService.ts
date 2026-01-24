export interface ElizaResponse {
  success: boolean;
  message: string;
  persona?: string;
  raw?: any;
}

export async function sendToEliza(userMessage: string): Promise<ElizaResponse> {
  try {
    const response = await fetch("http://127.0.0.1:8000/api/eliza/task", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ task_text: userMessage })
    });
    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        message: `Error ${response.status}: ${errorText || "Backend returned an error status."}`
      };
    }
    const data = await response.json();
    const message = data.eliza?.response || data.response || "No response received.";
    return {
      success: true,
      message: message,
      persona: data.persona,
      raw: data
    };
  } catch (error: any) {
    return {
      success: false,
      message: `Connection failed: ${error.message || "Failed to reach backend."}`
    };
  }
}
