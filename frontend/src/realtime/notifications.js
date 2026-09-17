function buildNotificationSocketUrl() {
  const apiBaseUrl =
    import.meta.env
      .VITE_API_BASE_URL;


  if (!apiBaseUrl) {
    throw new Error(
      "VITE_API_BASE_URL is not configured."
    );
  }


  const normalizedBaseUrl =
    apiBaseUrl.replace(
      /\/+$/,
      ""
    );


  if (
    normalizedBaseUrl.startsWith(
      "https://"
    )
  ) {
    return (
      normalizedBaseUrl.replace(
        "https://",
        "wss://"
      )
      + "/ws/notifications"
    );
  }


  if (
    normalizedBaseUrl.startsWith(
      "http://"
    )
  ) {
    return (
      normalizedBaseUrl.replace(
        "http://",
        "ws://"
      )
      + "/ws/notifications"
    );
  }


  throw new Error(
    (
      "VITE_API_BASE_URL must start "
      + "with http:// or https://"
    )
  );
}


export function connectNotificationSocket({
  onMessage,
  onReady,
  onOpen,
  onClose,
  onError,
}) {
  let socket =
    null;

  let reconnectTimer =
    null;

  let reconnectAttempts =
    0;

  let intentionallyClosed =
    false;


  const connect =
    () => {
      if (
        intentionallyClosed
      ) {
        return;
      }


      const token =
        localStorage.getItem(
          "harbor_access_token"
        );


      if (!token) {
        return;
      }


      try {
        socket =
          new WebSocket(
            buildNotificationSocketUrl()
          );


        socket.onopen =
          () => {
            reconnectAttempts =
              0;


            socket.send(
              JSON.stringify(
                {
                  type:
                    "authenticate",

                  token,
                }
              )
            );


            if (onOpen) {
              onOpen();
            }
          };


        socket.onmessage =
          (
            event
          ) => {
            try {
              const payload =
                JSON.parse(
                  event.data
                );


              if (
                payload.type
                === "ready"
              ) {
                if (onReady) {
                  onReady(
                    payload
                  );
                }

                return;
              }


              if (
                payload.type
                === "authentication_error"
              ) {
                console.error(
                  payload.message
                  || (
                    "Realtime authentication failed."
                  )
                );

                return;
              }


              if (
                payload.type
                === "pong"
              ) {
                return;
              }


              if (onMessage) {
                onMessage(
                  payload
                );
              }

            } catch (error) {
              console.error(
                (
                  "Unable to parse "
                  + "Harbor realtime message:"
                ),
                error
              );
            }
          };


        socket.onerror =
          (
            event
          ) => {
            if (onError) {
              onError(
                event
              );
            }
          };


        socket.onclose =
          (
            event
          ) => {
            if (onClose) {
              onClose(
                event
              );
            }


            if (
              intentionallyClosed
            ) {
              return;
            }


            if (
              event.code === 4401
              || event.code === 4403
            ) {
              return;
            }


            const delay =
              Math.min(
                (
                  1000
                  * (
                    2
                    ** reconnectAttempts
                  )
                ),
                15000
              );


            reconnectAttempts +=
              1;


            reconnectTimer =
              window.setTimeout(
                connect,
                delay
              );
          };


      } catch (error) {
        console.error(
          (
            "Unable to create "
            + "Harbor WebSocket:"
          ),
          error
        );
      }
    };


  connect();


  return () => {
    intentionallyClosed =
      true;


    if (
      reconnectTimer
    ) {
      window.clearTimeout(
        reconnectTimer
      );
    }


    if (
      socket
      && (
        socket.readyState
        === WebSocket.OPEN
        || socket.readyState
        === WebSocket.CONNECTING
      )
    ) {
      socket.close(
        1000,
        "Harbor page closed"
      );
    }
  };
}