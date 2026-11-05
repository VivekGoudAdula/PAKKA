"""
Test Suite for Owner Quick Entry Ledger Parser (15 Scenarios).
Verifies parsing of Hinglish ledger utterances into customer name, amounts, and dates.
"""

from __future__ import annotations

import pytest

from app.services.ledger_parser import parse_ledger_entry


@pytest.mark.parametrize(
    ("input_text", "expected_name", "expected_paid", "expected_balance", "expected_full"),
    [
        ("Ramesh ke kaam ho gaya 800 mile 500 baaki", "Ramesh", 800, 500, False),
        ("Sunita ji geyser repair 1200 full payment ho gayi", "Sunita", 1200, 0, True),
        ("Anil Kumar bathroom fitting 600 baaki kal dega", "Anil Kumar", 0, 600, False),
        ("Vikas plumbing 500 mile 300 baki parson tak", "Vikas", 500, 300, False),
        ("Pooja tap repair pura 450 clear", "Pooja", 450, 0, True),
        ("Deepak geyser coil change 1000 mile 500 baki somwar ko", "Deepak", 1000, 500, False),
        ("Rajesh motor fitting 2000 baki", "Rajesh", 0, 2000, False),
        ("Amit Sharma geyser service 700 pura mila", "Amit Sharma", 700, 0, True),
        ("Kavita kitchen pipe 350 mila kuch baki nahi", "Kavita", 350, 0, True),
        ("Manoj drainage clean 600 mile 200 baki 10 tareekh", "Manoj", 600, 200, False),
        ("Suresh geyser repair 900 mila sab clear", "Suresh", 900, 0, True),
        ("Mohit tap fitting 400 baaki somwar tak", "Mohit", 0, 400, False),
        ("Neha bathroom repair 1500 full payment", "Neha", 1500, 0, True),
        ("Pankaj plumbing 300 mile 200 baaki kal shaam", "Pankaj", 300, 200, False),
        ("Rohit pipe burst fix 1200 pura mila", "Rohit", 1200, 0, True),
    ],
)
def test_ledger_parser_scenarios(
    input_text: str,
    expected_name: str,
    expected_paid: int,
    expected_balance: int,
    expected_full: bool,
) -> None:
    parsed = parse_ledger_entry(input_text)
    assert parsed.customer_name == expected_name
    assert parsed.paid_amount == expected_paid
    assert parsed.balance == expected_balance
    assert parsed.is_fully_paid == expected_full


def test_ledger_parser_promise_date_extraction() -> None:
    res1 = parse_ledger_entry("Anil bathroom fitting 600 baaki kal dega")
    assert res1.promise_date == "kal"

    res2 = parse_ledger_entry("Vikas plumbing 500 mile 300 baki parson tak")
    assert res2.promise_date == "parson"

    res3 = parse_ledger_entry("Manoj drainage clean 600 mile 200 baki 10 tareekh")
    assert "10 tareekh" in res3.promise_date

