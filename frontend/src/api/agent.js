const API_BASE_URL =
  (
    import.meta.env.VITE_API_BASE_URL
    || ""
  ).replace(
    /\/$/,
    ""
  );


function parseSseBlock(
  block
) {
  const lines =
    block.split(
      "\n"
    );


  let eventName =
    "message";

  let dataText =
    "";


  for (
    const line
    of lines
  ) {

    if (
      line.startsWith(
        "event:"
      )
    ) {
      eventName =
        line
          .slice(6)
          .trim();

      continue;
    }


    if (
      line.startsWith(
        "data:"
      )
    ) {
      dataText +=
        line
          .slice(5)
          .trim();
    }
  }


  let data = {};


  if (dataText) {
    data =
      JSON.parse(
        dataText
      );
  }


  return {
    eventName,
    data,
  };
}


export async function streamAgentChat({
  message,
  conversationId,
  onToken,
}) {
  const token =
    localStorage.getItem(
      "harbor_access_token"
    );


  const response =
    await fetch(
      `${API_BASE_URL}/agent/chat/stream`,
      {
        method:
          "POST",

        headers: {
          "Content-Type":
            "application/json",

          ...(token
            ? {
              Authorization:
                `Bearer ${token}`,
            }
            : {}),
        },

        body:
          JSON.stringify({
            message,

            conversation_id:
              conversationId
              || null,
          }),
      }
    );


  if (!response.ok) {

    let detail =
      "Harbor could not process your request.";


    try {
      const body =
        await response.json();

      detail =
        body.detail
        || detail;

    } catch {
      // Keep fallback detail.
    }


    throw new Error(
      detail
    );
  }


  if (!response.body) {
    throw new Error(
      "Streaming is not supported by this browser."
    );
  }


  const reader =
    response.body.getReader();


  const decoder =
    new TextDecoder();


  let buffer =
    "";

  let finalResponse =
    null;


  while (true) {

    const {
      value,
      done,
    } = await reader.read();


    if (done) {
      break;
    }


    buffer +=
      decoder.decode(
        value,
        {
          stream: true,
        }
      );


    const blocks =
      buffer.split(
        "\n\n"
      );


    buffer =
      blocks.pop()
      || "";


    for (
      const block
      of blocks
    ) {

      if (!block.trim()) {
        continue;
      }


      const {
        eventName,
        data,
      } = parseSseBlock(
        block
      );


      if (
        eventName
        === "token"
      ) {
        onToken?.(
          data.content
          || ""
        );
      }


      if (
        eventName
        === "final"
      ) {
        finalResponse =
          data;
      }


      if (
        eventName
        === "error"
      ) {
        throw new Error(
          data.detail
          || (
            "Harbor could not "
            + "process your request."
          )
        );
      }
    }
  }


  if (!finalResponse) {
    throw new Error(
      "Harbor's response stream ended unexpectedly."
    );
  }


  return finalResponse;
}