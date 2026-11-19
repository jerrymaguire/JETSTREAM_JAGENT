import http from "node:http";

function writeChunk(response, payload) {
  response.write(`data: ${JSON.stringify(payload)}\n\n`);
}

const server = http.createServer(async (request, response) => {
  if (request.method !== "POST" || !request.url?.includes("/chat/completions")) {
    response.writeHead(404).end();
    return;
  }
  let raw = "";
  for await (const chunk of request) raw += chunk;
  const body = JSON.parse(raw || "{}");
  const hasToolResult = (body.messages ?? []).some((message) => message.role === "tool");
  response.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  const base = {
    id: "chatcmpl-mock",
    object: "chat.completion.chunk",
    created: Math.floor(Date.now() / 1000),
    model: body.model ?? "mock",
  };

  if (!hasToolResult) {
    writeChunk(response, {
      ...base,
      choices: [
        {
          index: 0,
          delta: {
            role: "assistant",
            tool_calls: [
              {
                index: 0,
                id: "call_mock_1",
                type: "function",
                function: { name: "list_files", arguments: "{\"limit\":5}" },
              },
            ],
          },
          finish_reason: null,
        },
      ],
    });
    writeChunk(response, {
      ...base,
      choices: [{ index: 0, delta: {}, finish_reason: "tool_calls" }],
    });
  } else {
    const text = "已通过 Pi 工具循环读取工作区文件。Agent Host 与 FastAPI 内部模型网关链路正常。";
    writeChunk(response, {
      ...base,
      choices: [{ index: 0, delta: { role: "assistant", content: "" }, finish_reason: null }],
    });
    for (let index = 0; index < text.length; index += 10) {
      writeChunk(response, {
        ...base,
        choices: [
          {
            index: 0,
            delta: { content: text.slice(index, index + 10) },
            finish_reason: null,
          },
        ],
      });
    }
    writeChunk(response, {
      ...base,
      choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
    });
  }
  response.write("data: [DONE]\n\n");
  response.end();
});

server.listen(8100, "127.0.0.1", () => {
  process.stdout.write("mock llm listening on 8100\n");
});

