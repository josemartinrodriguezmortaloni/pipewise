// Simple test script for chat endpoint
const testChatEndpoint = async () => {
  try {
    console.log("Testing chat endpoint...");

    const response = await fetch("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: [{ role: "user", content: "Hello, can you help me?" }],
      }),
    });

    console.log("Response status:", response.status);
    console.log(
      "Response headers:",
      Object.fromEntries(response.headers.entries())
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Error response:", errorText);
      return;
    }

    // Test streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    console.log("Reading stream...");
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      console.log("Chunk:", chunk);
    }

    console.log("Stream completed successfully");
  } catch (error) {
    console.error("Test failed:", error);
  }
};

// Run the test
testChatEndpoint();
