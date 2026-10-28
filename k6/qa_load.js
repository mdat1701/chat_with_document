import http from "k6/http";
import { check } from "k6";
import { Trend, Rate } from "k6/metrics";

export const answer_complete_ms = new Trend("answer_complete_ms");
export const ttft_ms = new Trend("ttft_ms");
export const answer_errors = new Rate("answer_errors");

export const options = {
  scenarios: {
    steady: { executor: "constant-arrival-rate", rate: 2, timeUnit: "1s", duration: "10m", preAllocatedVUs: 10, maxVUs: 15 },
    burst: { executor: "constant-arrival-rate", rate: 5, timeUnit: "1s", duration: "1m", startTime: "10m", preAllocatedVUs: 15, maxVUs: 20 },
  },
  thresholds: {
    answer_complete_ms: ["p(90)<15000"],
    ttft_ms: ["p(90)<3000"],
    answer_errors: ["rate<0.02"],
  },
};

export default function () {
  const base = __ENV.BASE_URL;
  const response = http.post(`${base}/api/v1/conversations`, null, { headers: { Cookie: __ENV.COOKIE } });
  check(response, { "conversation created": (r) => r.status === 201 });
  const id = response.json("conversation_id");
  const started = Date.now();
  const answer = http.post(`${base}/api/v1/conversations/${id}/questions`, JSON.stringify({ text: __ENV.QUESTION ?? "Tóm tắt tài liệu" }), {
    headers: { "Content-Type": "application/json", Cookie: __ENV.COOKIE, "X-CSRF-Token": __ENV.CSRF_TOKEN },
  });
  const done = (answer.body || "").indexOf("event: done");
  // k6 buffers the response body; waiting is the closest proxy for TTFT.
  // Full TTFT requires a streaming-capable runner and is recorded separately
  // by the OTel span in staging.
  ttft_ms.add(answer.timings.waiting);
  answer_complete_ms.add(Date.now() - started);
  answer_errors.add(answer.status >= 400 || done < 0);
  check(answer, { "question accepted": (r) => r.status === 200, "stream completed": () => done >= 0 });
}
