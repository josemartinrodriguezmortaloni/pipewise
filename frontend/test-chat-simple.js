// Simple test script for the basic chat endpoint
const testChatEndpoint = async () => {
  try {
    console.log("Testing simple chat endpoint...");

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

    const data = await response.json();
    console.log("Response data:", data);

    if (data.error) {
      console.error("API returned error:", data.error);
      if (data.details) {
        console.error("Error details:", data.details);
      }
    } else if (data.message) {
      console.log("✅ Success! AI response:", data.message.content);
    }
  } catch (error) {
    console.error("Test failed:", error);
  }
};

// Run the test
testChatEndpoint();
