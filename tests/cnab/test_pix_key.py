"""Tests for PIX key type detection and CPF/CNPJ validation.

Covers:
- detect_pix_key_type: all four SISPAG Nota 37 types + edge cases
- validate_cpf: check digit algorithm, all-same-digit rejection, punctuation stripping
- validate_cnpj: check digit algorithm, all-same-digit rejection, punctuation stripping
"""
import pytest
from cnab.pix_key import detect_pix_key_type, validate_cpf, validate_cnpj


class TestDetectPixKeyType:
    """Tests for detect_pix_key_type function."""

    def test_cpf_returns_03(self):
        assert detect_pix_key_type('51300907134') == '03'

    def test_cnpj_returns_03(self):
        assert detect_pix_key_type('12345678000195') == '03'

    def test_phone_e164_returns_01(self):
        assert detect_pix_key_type('+5511999887766') == '01'

    def test_phone_variant_returns_01(self):
        assert detect_pix_key_type('+5521912345678') == '01'

    def test_email_returns_02(self):
        assert detect_pix_key_type('joao@email.com') == '02'

    def test_email_case_insensitive_returns_02(self):
        assert detect_pix_key_type('JOAO@EMAIL.COM') == '02'

    def test_uuid_returns_04(self):
        assert detect_pix_key_type('123e4567-e89b-12d3-a456-426614174000') == '04'

    def test_strips_whitespace(self):
        assert detect_pix_key_type('  51300907134  ') == '03'

    def test_empty_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            detect_pix_key_type('')

    def test_whitespace_only_raises_valueerror(self):
        with pytest.raises(ValueError):
            detect_pix_key_type('   ')

    def test_invalid_key_raises_valueerror(self):
        with pytest.raises(ValueError):
            detect_pix_key_type('invalid-key')

    def test_too_short_raises_valueerror(self):
        with pytest.raises(ValueError):
            detect_pix_key_type('12345')


class TestValidateCpf:
    """Tests for validate_cpf function."""

    def test_known_valid_cpf(self):
        assert validate_cpf('51300907134') is True

    def test_another_valid_cpf(self):
        assert validate_cpf('52998224725') is True

    def test_wrong_check_digit_returns_false(self):
        assert validate_cpf('51300907135') is False

    def test_all_same_digits_returns_false(self):
        assert validate_cpf('11111111111') is False

    def test_all_zeros_returns_false(self):
        assert validate_cpf('00000000000') is False

    def test_too_short_returns_false(self):
        assert validate_cpf('1234567') is False

    def test_too_long_returns_false(self):
        assert validate_cpf('123456789012') is False

    def test_formatted_cpf_with_punctuation(self):
        assert validate_cpf('513.009.071-34') is True


class TestValidateCnpj:
    """Tests for validate_cnpj function."""

    def test_known_valid_cnpj(self):
        assert validate_cnpj('11222333000181') is True

    def test_wrong_check_digit_returns_false(self):
        assert validate_cnpj('11222333000182') is False

    def test_all_same_digits_returns_false(self):
        assert validate_cnpj('11111111111111') is False

    def test_too_short_returns_false(self):
        assert validate_cnpj('12345') is False

    def test_formatted_cnpj_with_punctuation(self):
        assert validate_cnpj('11.222.333/0001-81') is True
