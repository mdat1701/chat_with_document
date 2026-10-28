from __future__ import annotations

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """Bạn là trợ lý hỏi đáp dựa trên tài liệu.
Chỉ sử dụng các đoạn trích được cung cấp. Nếu không đủ bằng chứng, trả lời
rằng không tìm thấy thông tin và không suy đoán. Mỗi nhận định thực tế phải
có citation dạng [doc:<document_id> p:<page_start>-<page_end>].
Trả lời cùng ngôn ngữ với câu hỏi, hỗ trợ tiếng Việt và tiếng Anh."""


def build_prompt(question: str, contexts: list[dict[str, object]]) -> str:
    evidence = "\n\n".join(
        f"[doc:{item['document_id']} p:{item['page_start']}-{item['page_end']}]\n{item['content']}"
        for item in contexts
    )
    instruction = (
        "Tổng hợp thông tin từ mọi tài liệu liên quan. Nếu có mâu thuẫn, "
        "nêu cả hai giá trị và nguồn tương ứng."
    )
    return f"Câu hỏi: {question}\n{instruction}\n\nBằng chứng:\n{evidence}"
