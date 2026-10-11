import 'package:flutter/services.dart';

/// Card-number helpers for the Premium card form. They only check the
/// format; whether a card can actually be charged is for the payment
/// gateway to decide.
class CardUtils {
  CardUtils._();

  static String digits(String s) => s.replaceAll(RegExp(r'\D'), '');

  static String brandOf(String number) {
    final d = digits(number);
    if (d.startsWith('4')) return 'Visa';
    if (RegExp(r'^(5[1-5]|2[2-7])').hasMatch(d)) return 'Mastercard';
    if (RegExp(r'^3[47]').hasMatch(d)) return 'Amex';
    return 'Card';
  }

  static int cvcLength(String brand) => brand == 'Amex' ? 4 : 3;

  /// Luhn checksum, which every real card number passes.
  static bool luhn(String number) {
    final d = digits(number);
    if (d.length < 12) return false;
    var sum = 0;
    var alt = false;
    for (var i = d.length - 1; i >= 0; i--) {
      var n = d.codeUnitAt(i) - 48;
      if (alt) {
        n *= 2;
        if (n > 9) n -= 9;
      }
      sum += n;
      alt = !alt;
    }
    return sum % 10 == 0;
  }

  static String? validateNumber(String? value) {
    final d = digits(value ?? '');
    if (d.isEmpty) return 'Enter your card number';
    final expected = brandOf(d) == 'Amex' ? 15 : 16;
    if (d.length < expected || !luhn(d)) return 'Check the card number';
    return null;
  }

  /// Parses "MM/YY" into (month, four-digit year), or null.
  static (int, int)? parseExpiry(String value) {
    final m = RegExp(r'^(\d{2})/(\d{2})$').firstMatch(value.replaceAll(' ', ''));
    if (m == null) return null;
    final month = int.parse(m.group(1)!);
    final year = 2000 + int.parse(m.group(2)!);
    if (month < 1 || month > 12) return null;
    return (month, year);
  }

  static String? validateExpiry(String? value, {DateTime? now}) {
    final parsed = parseExpiry(value ?? '');
    if (parsed == null) return 'Use MM/YY';
    final today = now ?? DateTime.now();
    // A card is valid through the last day of its expiry month.
    final firstDayAfterExpiry = DateTime(parsed.$2, parsed.$1 + 1);
    if (!firstDayAfterExpiry.isAfter(DateTime(today.year, today.month))) return 'This card has expired';
    return null;
  }

  static String? validateCvc(String? value, String brand) {
    final d = digits(value ?? '');
    if (d.length != cvcLength(brand)) return '${cvcLength(brand)} digits';
    return null;
  }

  /// Longest name a card can print.
  static const int maxNameLength = 26;

  // Letters in any language, plus the space . ' - found in real names.
  static final _nameChars = RegExp(r"^\p{L}[\p{L} .'\-]*$", unicode: true);

  static String? validateName(String? value) {
    final name = (value ?? '').trim();
    if (name.isEmpty) return 'Enter the name on your card';
    if (RegExp(r'\d').hasMatch(name)) return "A name can't contain numbers";
    if (!_nameChars.hasMatch(name)) return "Use letters only (spaces, - and ' are fine)";
    if (RegExp(r'\p{L}', unicode: true).allMatches(name).length < 2) return 'Enter the full name on your card';
    if (name.length > maxNameLength) return 'Use the name as printed (max $maxNameLength characters)';
    if (RegExp(r"[ .'\-]{2,}").hasMatch(name)) return 'Check the spacing and punctuation';
    return null;
  }

  /// Trims and collapses repeated spaces: "  ali   khan " -> "ali khan".
  static String cleanName(String value) => value.trim().replaceAll(RegExp(r'\s+'), ' ');
}

/// Groups the card number as "4242 4242 4242 4242" (Amex: 4-6-5).
class CardNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    final d = CardUtils.digits(newValue.text);
    final amex = CardUtils.brandOf(d) == 'Amex';
    final max = amex ? 15 : 16;
    final clipped = d.length > max ? d.substring(0, max) : d;
    final groups = amex ? [4, 6, 5] : [4, 4, 4, 4];
    final buf = StringBuffer();
    var i = 0;
    for (final g in groups) {
      if (i >= clipped.length) break;
      if (buf.isNotEmpty) buf.write(' ');
      final end = (i + g).clamp(0, clipped.length);
      buf.write(clipped.substring(i, end));
      i = end;
    }
    final text = buf.toString();
    return TextEditingValue(text: text, selection: TextSelection.collapsed(offset: text.length));
  }
}

/// Formats the expiry as "MM/YY" while typing.
class ExpiryFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    var d = CardUtils.digits(newValue.text);
    if (d.length > 4) d = d.substring(0, 4);
    final text = d.length > 2 ? '${d.substring(0, 2)}/${d.substring(2)}' : d;
    return TextEditingValue(text: text, selection: TextSelection.collapsed(offset: text.length));
  }
}
