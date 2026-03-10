import pytest
from uuid import uuid4
from core.models import CallAnalysis, CallRecord, SpanRecord, QAPairRecord
from ingestion.pipeline import create_chunks_from_analysis

def test_chunking_large_prepared_span():
    call_id = uuid4()
    call = CallRecord(ticker="AAPL", transcript_json="", transcript_text="", token_count=1000, prepared_len=1000, qa_len=0, id=call_id)
    analysis = CallAnalysis(call=call, speakers=[], spans=[], keywords=[], topics=[], takeaways=[], qa_pairs=[])
    
    huge_text = "word " * 2000
    span = SpanRecord(
        id=uuid4(),
        call_id=call_id,
        speaker_name="Tim Cook",
        span_type="turn",
        text=huge_text.strip(),
        section="prepared",
        sequence_order=1
    )
    analysis.spans.append(span)
    
    chunks = create_chunks_from_analysis(analysis, max_chars=4000, overlap_chars=500)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 4500
        assert chunk.chunk_type == "prepared"

def test_chunking_overlap():
    call_id = uuid4()
    call = CallRecord(ticker="AAPL", transcript_json="", transcript_text="", token_count=1000, prepared_len=1000, qa_len=0, id=call_id)
    analysis = CallAnalysis(call=call, speakers=[], spans=[], keywords=[], topics=[], takeaways=[], qa_pairs=[])
    
    text1 = "A" * 3000
    text2 = "B" * 3000
    text3 = "C" * 3000
    
    analysis.spans.extend([
        SpanRecord(id=uuid4(), call_id=call_id, speaker_name="S1", text=text1, section="prepared", span_type="turn", sequence_order=1),
        SpanRecord(id=uuid4(), call_id=call_id, speaker_name="S2", text=text2, section="prepared", span_type="turn", sequence_order=2),
        SpanRecord(id=uuid4(), call_id=call_id, speaker_name="S3", text=text3, section="prepared", span_type="turn", sequence_order=3)
    ])
    
    chunks = create_chunks_from_analysis(analysis, max_chars=4000, overlap_chars=500)
    assert len(chunks) > 1

def test_chunking_qa_exchanges():
    call_id = uuid4()
    call = CallRecord(ticker="AAPL", transcript_json="", transcript_text="", token_count=1000, prepared_len=1000, qa_len=0, id=call_id)
    analysis = CallAnalysis(call=call, speakers=[], spans=[], keywords=[], topics=[], takeaways=[], qa_pairs=[])
    
    s1_id, s2_id, s3_id, s4_id = uuid4(), uuid4(), uuid4(), uuid4()
    s1 = SpanRecord(id=s1_id, call_id=call_id, speaker_name="Q1", text="Question?", section="qa", span_type="turn", sequence_order=1)
    s2 = SpanRecord(id=s2_id, call_id=call_id, speaker_name="A1", text="Answer.", section="qa", span_type="turn", sequence_order=2)
    s3 = SpanRecord(id=s3_id, call_id=call_id, speaker_name="Q2", text="Question 2? " * 500, section="qa", span_type="turn", sequence_order=3)
    s4 = SpanRecord(id=s4_id, call_id=call_id, speaker_name="A2", text="Answer 2. " * 500, section="qa", span_type="turn", sequence_order=4)

    analysis.spans.extend([s1, s2, s3, s4])
    analysis.qa_pairs.extend([
        QAPairRecord(exchange_order=1, question_span_ids=[s1_id], answer_span_ids=[s2_id]),
        QAPairRecord(exchange_order=2, question_span_ids=[s3_id], answer_span_ids=[s4_id])
    ])

    chunks = create_chunks_from_analysis(analysis, max_chars=4000, overlap_chars=500)
    
    assert len(chunks) >= 3
    assert chunks[0].chunk_type == "qa"
    assert chunks[1].chunk_type == "qa"
