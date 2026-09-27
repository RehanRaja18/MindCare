import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../main.dart';
import '../../widgets/common/aurora_background.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/sos_button.dart';
import '../auth/sign_in_screen.dart';
import 'sign_up_screen.dart';

// Palette of the marketing site's front page, so the app's first screen
// reads as the same product as the web hero and the splash.
const _cream = Color(0xFFF5F0E8);
const _ink = Color(0xFF111827); // gray-900: web headline + primary button
const _body = Color(0xFF4B5563); // gray-600
const _eyebrow = Color(0xFF6B7280); // gray-500
const _outline = Color(0xFFE5E7EB); // gray-200

// Web headline curve: cubic-bezier(0.22, 1, 0.36, 1).
const _easeOutQuint = Cubic(0.22, 1, 0.36, 1);

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen>
    with TickerProviderStateMixin {
  // Timings mirror the web hero: words stagger in 0.13s apart, each taking
  // 0.75s. The first delay also covers the splash's 0.7s cross-fade.
  static const _startDelay = 0.45;
  static const _stagger = 0.13;
  static const _wordDuration = 0.75;
  static const _wordCount = 3;
  static const _entrySeconds = 2.4;

  late final AnimationController _entry = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: (_entrySeconds * 1000).round()),
  )..forward();

  // Continuous drift after the entrance, like the web's `floating-text`.
  late final AnimationController _float = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 4500),
  )..repeat();

  // Slow sheen across "mind", like the web's `animate-text-shimmer`.
  late final AnimationController _shimmer = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  )..repeat();

  late final AnimationController _breathe = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _entry.dispose();
    _float.dispose();
    _shimmer.dispose();
    _breathe.dispose();
    super.dispose();
  }

  Animation<double> _interval(double startSec, double durationSec) {
    final begin = (startSec / _entrySeconds).clamp(0.0, 1.0);
    final end = ((startSec + durationSec) / _entrySeconds).clamp(0.0, 1.0);
    return CurvedAnimation(
      parent: _entry,
      curve: Interval(begin, end, curve: _easeOutQuint),
    );
  }

  Widget _word(int index, Widget child) {
    return _HeadlineWord(
      entrance: _interval(_startDelay + index * _stagger, _wordDuration),
      float: _float,
      floatPhase: index * 0.3 / 4.5,
      child: child,
    );
  }

  /// Fade + rise for the copy and buttons once the headline has landed.
  Widget _reveal(double startSec, Widget child) {
    final anim = _interval(startSec, 0.7);
    return AnimatedBuilder(
      animation: anim,
      builder: (context, child) => Opacity(
        opacity: anim.value,
        child: Transform.translate(
          offset: Offset(0, 18 * (1 - anim.value)),
          child: child,
        ),
      ),
      child: child,
    );
  }

  void _push(Widget screen) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => MobileFrame(child: screen)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final headline = GoogleFonts.playfairDisplay(
      fontSize: 38,
      height: 1.12,
      fontWeight: FontWeight.w600,
      color: _ink,
      letterSpacing: -0.5,
    );

    return Scaffold(
      backgroundColor: _cream,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const AuroraBackground(),
          Positioned(
            top: -70,
            right: -90,
            child: _BreathingOrb(animation: _breathe),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 20),
                  _reveal(
                    0.3,
                    Image.asset(
                      'assets/images/mindcare_logo.png',
                      height: 64,
                      fit: BoxFit.contain,
                    ),
                  ),
                  const Spacer(flex: 2),
                  _reveal(
                    0.35,
                    Text(
                      'MENTAL CARE · WEEKLY · SINCE 2026',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        letterSpacing: 2.2,
                        fontWeight: FontWeight.w600,
                        color: _eyebrow,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  _word(0, Text('A quieter', style: headline)),
                  Wrap(
                    crossAxisAlignment: WrapCrossAlignment.end,
                    children: [
                      _word(
                        1,
                        _ShimmerText(
                          'mind',
                          animation: _shimmer,
                          style: headline.copyWith(
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ),
                      _word(2, Text('starts here.', style: headline)),
                    ],
                  ),
                  const SizedBox(height: 18),
                  _reveal(
                    _startDelay + _wordCount * _stagger + 0.25,
                    Text(
                      "Therapy that fits your day. Care that doesn't judge. "
                      'Quiet tools for the loud moments.',
                      style: GoogleFonts.inter(
                        fontSize: 16,
                        height: 1.55,
                        color: _body,
                      ),
                    ),
                  ),
                  const Spacer(flex: 2),
                  _reveal(
                    _startDelay + _wordCount * _stagger + 0.45,
                    PrimaryButton(
                      label: 'Create your account',
                      icon: null,
                      backgroundColor: _ink,
                      onPressed: () => _push(const SignUpScreen()),
                    ),
                  ),
                  const SizedBox(height: 14),
                  _reveal(
                    _startDelay + _wordCount * _stagger + 0.6,
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => _push(const SignInScreen()),
                            style: OutlinedButton.styleFrom(
                              backgroundColor:
                                  Colors.white.withValues(alpha: 0.85),
                              padding: const EdgeInsets.symmetric(
                                vertical: 18,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(18),
                              ),
                              side: const BorderSide(color: _outline),
                            ),
                            child: Text(
                              'I already have one',
                              style: GoogleFonts.inter(
                                fontSize: 15,
                                fontWeight: FontWeight.w500,
                                color: _ink,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        const SosButton(),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// One headline phrase: swings and focuses into place (fade, rise, scale,
/// un-rotate, un-blur), then keeps drifting gently, offset by [floatPhase]
/// so the words never move in lockstep.
class _HeadlineWord extends StatelessWidget {
  const _HeadlineWord({
    required this.entrance,
    required this.float,
    required this.floatPhase,
    required this.child,
  });

  final Animation<double> entrance;
  final Animation<double> float;
  final double floatPhase;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([entrance, float]),
      builder: (context, child) {
        final t = entrance.value;
        final drift = -2.5 *
            (1 - math.cos(2 * math.pi * (float.value + floatPhase)));
        final blur = 12 * (1 - t);

        Widget word = Transform.translate(
          offset: Offset(0, 34 * (1 - t) + drift),
          child: Transform.rotate(
            angle: -3 * math.pi / 180 * (1 - t),
            child: Transform.scale(scale: 0.88 + 0.12 * t, child: child),
          ),
        );
        if (blur > 0.05) {
          word = ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
            child: word,
          );
        }
        return Opacity(opacity: t.clamp(0.0, 1.0), child: word);
      },
      child: child,
    );
  }
}

/// Text filled with the web's orange → rose → purple gradient, sliding
/// slowly across the letters.
class _ShimmerText extends StatelessWidget {
  const _ShimmerText(this.text, {required this.animation, required this.style});

  final String text;
  final Animation<double> animation;
  final TextStyle style;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) => ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (bounds) {
          // Gradient is twice the text width and mirrored, so sliding it by
          // one full span loops without a visible seam.
          final span = bounds.width * 2;
          return const LinearGradient(
            colors: [
              Color(0xFFF97316), // orange-500
              Color(0xFFF43F5E), // rose-500
              Color(0xFFA855F7), // purple-500
              Color(0xFFF43F5E),
              Color(0xFFF97316),
            ],
            tileMode: TileMode.repeated,
          ).createShader(
            Rect.fromLTWH(-animation.value * span, 0, span, bounds.height),
          );
        },
        child: child,
      ),
      // Right padding keeps the italic overhang inside the shader bounds.
      child: Padding(
        padding: const EdgeInsets.only(right: 10),
        child: Text(text, style: style.copyWith(color: Colors.white)),
      ),
    );
  }
}

/// The top-right circle, in the splash/web warm palette, breathing slowly
/// like the web hero's glow blobs.
class _BreathingOrb extends StatelessWidget {
  const _BreathingOrb({required this.animation});

  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) {
        final t = Curves.easeInOut.transform(animation.value);
        return Transform.scale(scale: 1 + 0.06 * t, child: child);
      },
      child: Container(
        width: 290,
        height: 290,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFFED7AA), // orange-200
              Color(0xFFFDBA74), // orange-300
              Color(0xFFFDA4AF), // rose-300
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFFDBA74).withValues(alpha: 0.4),
              blurRadius: 60,
              spreadRadius: 4,
            ),
          ],
        ),
      ),
    );
  }
}
