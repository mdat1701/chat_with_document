import http from "k6/http";

export const options = {
  scenarios: { burst: { executor: "constant-arrival-rate", rate: 10, timeUnit: "1s", duration: "50s", preAllocatedVUs: 10, maxVUs: 20 } },
};

export default function () {
  const file = open(__ENV.PDF_PATH ?? "../frontend/e2e/fixtures/sample.pdf", "b");
  http.post(`${__ENV.BASE_URL}/api/v1/documents`, { file: http.file(file, "sample.pdf", "application/pdf") }, {
    headers: { Cookie: __ENV.COOKIE, "X-CSRF-Token": __ENV.CSRF_TOKEN },
  });
}
