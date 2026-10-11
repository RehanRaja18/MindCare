import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/card_utils.dart';
import '../../models/premium_data.dart';

/// Card details entry with a live preview. Call [CardFormState.submit] to
/// validate; it returns a [PaymentCard] holding only brand, last four and
/// expiry. The full number and CVC are dropped as soon as the form is
/// disposed and are never stored or logged.
class CardForm extends StatefulWidget {
  const CardForm({super.key});

  @override
  State<CardForm> createState() => CardFormState();
}

class CardFormState extends State<CardForm> {
  final _formKey = GlobalKey<FormState>();
  final _number = TextEditingController();
  final _expiry = TextEditingController();
  final _cvc = TextEditingController();
  final _name = TextEditingController();

  String get _brand => CardUtils.brandOf(_number.text);

  @override
  void initState() {
    super.initState();
    for (final c in [_number, _expiry, _name]) {
      c.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    _number.dispose();
    _expiry.dispose();
    _cvc.dispose();
    _name.dispose();
    super.dispose();
  }

  /// Validates the form; returns the card to keep, or null if something is wrong.
  PaymentCard? submit() {
    if (!_formKey.currentState!.validate()) return null;
    final digits = CardUtils.digits(_number.text);
    final expiry = CardUtils.parseExpiry(_expiry.text)!;
    return PaymentCard(
      brand: _brand,
      last4: digits.substring(digits.length - 4),
      expMonth: expiry.$1,
      expYear: expiry.$2,
      holderName: CardUtils.cleanName(_name.text),
    );
  }

  InputDecoration _decoration(String hint, {Widget? suffix}) => InputDecoration(
        hintText: hint,
        hintStyle: AppTextStyles.body(size: 15, color: AppColors.textLabel),
        filled: true,
        fillColor: Colors.white,
        suffixIcon: suffix,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.border)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.border)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.progressActive, width: 1.4)),
        errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.sos)),
        focusedErrorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.sos, width: 1.4)),
      );

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CardPreview(
            brand: _brand,
            number: _number.text,
            name: _name.text,
            expiry: _expiry.text,
          ),
          const SizedBox(height: 20),
          Text('CARD NUMBER', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          TextFormField(
            key: const Key('card-number'),
            controller: _number,
            keyboardType: TextInputType.number,
            autofillHints: const [AutofillHints.creditCardNumber],
            inputFormatters: [CardNumberFormatter()],
            validator: CardUtils.validateNumber,
            style: AppTextStyles.body(size: 16, color: AppColors.textDark).copyWith(letterSpacing: 1.2),
            decoration: _decoration('1234 5678 9012 3456', suffix: const Icon(Icons.credit_card, color: AppColors.textMuted)),
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('EXPIRY', style: AppTextStyles.label()),
                    const SizedBox(height: 8),
                    TextFormField(
                      key: const Key('card-expiry'),
                      controller: _expiry,
                      keyboardType: TextInputType.number,
                      autofillHints: const [AutofillHints.creditCardExpirationDate],
                      inputFormatters: [ExpiryFormatter()],
                      validator: CardUtils.validateExpiry,
                      style: AppTextStyles.body(size: 16, color: AppColors.textDark),
                      decoration: _decoration('MM/YY'),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('CVC', style: AppTextStyles.label()),
                    const SizedBox(height: 8),
                    TextFormField(
                      key: const Key('card-cvc'),
                      controller: _cvc,
                      keyboardType: TextInputType.number,
                      obscureText: true,
                      autofillHints: const [AutofillHints.creditCardSecurityCode],
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(4)],
                      validator: (v) => CardUtils.validateCvc(v, _brand),
                      style: AppTextStyles.body(size: 16, color: AppColors.textDark),
                      decoration: _decoration(_brand == 'Amex' ? '1234' : '123', suffix: const Icon(Icons.lock_outline, size: 18, color: AppColors.textMuted)),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text('NAME ON CARD', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          TextFormField(
            key: const Key('card-name'),
            controller: _name,
            textCapitalization: TextCapitalization.words,
            autofillHints: const [AutofillHints.creditCardName],
            // Block digits and symbols as they are typed; the validator explains the rest.
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r"[\p{L} .'\-]", unicode: true)),
              LengthLimitingTextInputFormatter(CardUtils.maxNameLength),
            ],
            validator: CardUtils.validateName,
            style: AppTextStyles.body(size: 16, color: AppColors.textDark),
            decoration: _decoration('As shown on the card'),
          ),
        ],
      ),
    );
  }
}

/// A dark-green card that mirrors what the patient types.
class CardPreview extends StatelessWidget {
  const CardPreview({super.key, required this.brand, required this.number, required this.name, required this.expiry});
  final String brand;
  final String number;
  final String name;
  final String expiry;

  String get _maskedNumber {
    final d = CardUtils.digits(number);
    final amex = brand == 'Amex';
    final total = amex ? 15 : 16;
    // Show what has been typed, with the middle digits hidden once it's long enough.
    final chars = List.generate(total, (i) {
      if (i >= d.length) return '•';
      final hidden = d.length > 8 && i >= 4 && i < total - 4;
      return hidden ? '•' : d[i];
    });
    final groups = amex ? [4, 6, 5] : [4, 4, 4, 4];
    final buf = StringBuffer();
    var i = 0;
    for (final g in groups) {
      if (buf.isNotEmpty) buf.write('  ');
      buf.write(chars.sublist(i, i + g).join());
      i += g;
    }
    return buf.toString();
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.62,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.breathGradientStart, AppColors.primaryDark],
          ),
          boxShadow: [BoxShadow(color: AppColors.primaryDark.withValues(alpha: 0.25), blurRadius: 18, offset: const Offset(0, 8))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 38,
                  height: 28,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(6),
                    gradient: const LinearGradient(colors: [Color(0xFFF0DEB9), Color(0xFFC79A56)]),
                  ),
                ),
                const Spacer(),
                Text(
                  brand == 'Card' ? '' : brand.toUpperCase(),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, letterSpacing: 1.2, fontSize: 14),
                ),
              ],
            ),
            const Spacer(),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                _maskedNumber,
                style: const TextStyle(color: Colors.white, fontSize: 20, letterSpacing: 1.5, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('CARD HOLDER', style: TextStyle(color: Colors.white60, fontSize: 9, letterSpacing: 1)),
                      const SizedBox(height: 2),
                      Text(
                        name.trim().isEmpty ? 'YOUR NAME' : name.trim().toUpperCase(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600, letterSpacing: 0.8),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Text('EXPIRES', style: TextStyle(color: Colors.white60, fontSize: 9, letterSpacing: 1)),
                    const SizedBox(height: 2),
                    Text(
                      expiry.isEmpty ? 'MM/YY' : expiry,
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
