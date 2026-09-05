export const TYPE_CONTROL = 1;
export const TYPE_PCM_IN = 2;
export const TYPE_PCM_OUT = 3;
export const MAX_FRAME_BYTES = 16384;
export const CONTROL_OPS = new Set(["bootstrap", "gate", "flush", "stop", "state", "error"]);

export class ProtocolError extends Error {
  constructor(message) {
    super(message);
    this.name = "ProtocolError";
  }
}

export function encodeFrame(type, payload) {
  if (![TYPE_CONTROL, TYPE_PCM_IN, TYPE_PCM_OUT].includes(type)) {
    throw new ProtocolError("unsupported frame type");
  }
  const body = Buffer.concat([Buffer.from([type]), payload]);
  if (body.length > MAX_FRAME_BYTES) {
    throw new ProtocolError("frame exceeds maximum size");
  }
  const header = Buffer.alloc(4);
  header.writeUInt32LE(body.length, 0);
  return Buffer.concat([header, body]);
}

export function encodeControl(message) {
  if (!message || !CONTROL_OPS.has(message.op)) {
    throw new ProtocolError("unsupported control op");
  }
  return encodeFrame(TYPE_CONTROL, Buffer.from(JSON.stringify(message), "utf8"));
}

export function decodeControl(payload) {
  let message;
  try {
    message = JSON.parse(payload.toString("utf8"));
  } catch {
    throw new ProtocolError("control payload is not json");
  }
  if (!message || typeof message !== "object" || !CONTROL_OPS.has(message.op)) {
    throw new ProtocolError("control payload is invalid");
  }
  return message;
}

export class FrameDecoder {
  constructor() {
    this.buffer = Buffer.alloc(0);
  }

  push(chunk) {
    if (!chunk || chunk.length === 0) {
      if (this.buffer.length > 0) {
        throw new ProtocolError("incomplete frame");
      }
      return [];
    }
    this.buffer = Buffer.concat([this.buffer, chunk]);
    const frames = [];
    while (this.buffer.length >= 4) {
      const length = this.buffer.readUInt32LE(0);
      if (length < 1 || length > MAX_FRAME_BYTES) {
        throw new ProtocolError("malformed frame length");
      }
      if (this.buffer.length < 4 + length) {
        break;
      }
      const body = this.buffer.subarray(4, 4 + length);
      this.buffer = this.buffer.subarray(4 + length);
      const type = body[0];
      if (![TYPE_CONTROL, TYPE_PCM_IN, TYPE_PCM_OUT].includes(type)) {
        throw new ProtocolError("unsupported frame type");
      }
      frames.push({ type, payload: body.subarray(1) });
    }
    return frames;
  }

  close() {
    if (this.buffer.length > 0) {
      throw new ProtocolError("incomplete frame");
    }
  }
}
