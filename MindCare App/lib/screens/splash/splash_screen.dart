import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../main.dart';
import '../onboarding/welcome_screen.dart';

// Same cream as the Welcome screen and the web front page, so the hand-off
// from splash to Welcome is seamless.
const _cream = Color(0xFFF5F0E8);
const _ink = Color(0xFF111827);
const _glow = Color(0xFFFDBA74); // orange-300
const _ripple = Color(0xFFFB923C); // orange-400

const _easeOutQuint = Cubic(0.22, 1, 0.36, 1);

/// Plain background; all the motion lives in the logo:
///  1. the mark is "drawn" by a circular sweep while it scales and focuses in,
///  2. a warm halo blooms behind it and calm ripples keep radiating out,
///  3. MINDCARE settles letter by letter from wide spacing,
///  4. the tagline fades up, then the mark breathes until hand-off.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  static const _entrySeconds = 2.6;
  static const _splashDuration = Duration(milliseconds: 3800);

  late final AnimationController _entry = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: (_entrySeconds * 1000).round()),
  )..forward();

  late final AnimationController _ripples = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2600),
  );

  late final AnimationController _breathe = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3200),
  );

  late final Animation<double> _sweep = _interval(0.0, 1.1, Curves.easeInOutCubic);
  late final Animation<double> _markIn = _interval(0.0, 1.2, _easeOutQuint);
  late final Animation<double> _halo = _interval(0.4, 1.4, Curves.easeOut);
  late final Animation<double> _word = _interval(0.9, 1.9, _easeOutQuint);
  late final Animation<double> _tagline = _interval(1.6, 2.6, Curves.easeOut);

  @override
  void initState() {
    super.initState();

    // Ripples and breathing start once the mark has landed.
    Future.delayed(const Duration(milliseconds: 1100), () {
      if (!mounted) return;
      _ripples.repeat();
      _breathe.repeat();
    });

    Future.delayed(_splashDuration, () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          transitionDuration: const Duration(milliseconds: 700),
          pageBuilder: (_, __, ___) =>
              const MobileFrame(child: WelcomeScreen()),
          transitionsBuilder: (_, animation, __, child) {
            return FadeTransition(
              opacity: CurvedAnimation(
                parent: animation,
                curve: Curves.easeInOut,
              ),
              child: child,
            );
          },
        ),
      );
    });
  }

  Animation<double> _interval(double startSec, double endSec, Curve curve) {
    return CurvedAnimation(
      parent: _entry,
      curve: Interval(
        startSec / _entrySeconds,
        (endSec / _entrySeconds).clamp(0.0, 1.0),
        curve: curve,
      ),
    );
  }

  @override
  void dispose() {
    _entry.dispose();
    _ripples.dispose();
    _breathe.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _cream,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 300,
              height: 240,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  _RippleRings(animation: _ripples),
                  _Halo(animation: _halo, breathe: _breathe),
                  _AnimatedMark(
                    sweep: _sweep,
                    entrance: _markIn,
                    breathe: _breathe,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            _Wordmark(animation: _word),
            const SizedBox(height: 10),
            _Tagline(animation: _tagline),
          ],
        ),
      ),
    );
  }
}

/// The circular mark from the logo PNG (the artwork above the wordmark),
/// revealed by a clockwise sweep while it scales up and un-blurs.
class _AnimatedMark extends StatelessWidget {
  const _AnimatedMark({
    required this.sweep,
    required this.entrance,
    required this.breathe,
  });

  final Animation<double> sweep;
  final Animation<double> entrance;
  final Animation<double> breathe;

  // In mindcare_logo.png (435×384) the mark sits in rows 18–258 and
  // columns 102–332; the wordmark starts below row 283.
  static const _imageWidth = 270.0;

  @override
  Widget build(BuildContext context) {
    final mark = ClipRect(
      child: Align(
        alignment: Alignment.topCenter,
        widthFactor: 0.6,
        heightFactor: 0.7,
        child: Image.asset(
          'assets/images/mindcare_logo.png',
          width: _imageWidth,
          fit: BoxFit.contain,
        ),
      ),
    );

    return AnimatedBuilder(
      animation: Listenable.merge([sweep, entrance, breathe]),
      builder: (context, child) {
        final t = entrance.value;
        final breath = 1 + 0.03 * math.sin(breathe.value * 2 * math.pi);
        final blur = 8 * (1 - t);

        Widget content = ClipPath(
          clipper: _SweepClipper(sweep.value),
          child: child,
        );
        if (blur > 0.05) {
          content = ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
            child: content,
          );
        }
        return Opacity(
          opacity: t.clamp(0.0, 1.0),
          child: Transform.rotate(
            angle: -0.35 * (1 - t),
            child: Transform.scale(
              scale: (0.72 + 0.28 * t) * breath,
              child: content,
            ),
          ),
        );
      },
      child: mark,
    );
  }
}

/// Pie-slice clip growing clockwise from 12 o'clock, so the mark looks
/// like it's being drawn around its ring.
class _SweepClipper extends CustomClipper<Path> {
  _SweepClipper(this.progress);

  final double progress;

  @override
  Path getClip(Size size) {
    if (progress >= 1) return Path()..addRect(Offset.zero & size);
    final center = size.center(Offset.zero);
    final radius = size.longestSide;
    return Path()
      ..moveTo(center.dx, center.dy)
      ..arcTo(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2,
        2 * math.pi * progress,
        false,
      )
      ..close();
  }

  @override
  bool shouldReclip(_SweepClipper oldClipper) =>
      oldClipper.progress != progress;
}

/// Soft warm glow blooming behind the mark, breathing with it.
class _Halo extends StatelessWidget {
  const _Halo({required this.animation, required this.breathe});

  final Animation<double> animation;
  final Animation<double> breathe;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([animation, breathe]),
      builder: (context, _) {
        final t = animation.value;
        final breath = 1 + 0.06 * math.sin(breathe.value * 2 * math.pi);
        return Transform.scale(
          scale: (0.5 + 0.5 * t) * breath,
          child: Container(
            width: 220,
            height: 220,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  _glow.withValues(alpha: 0.55 * t),
                  const Color(0xFFFDA4AF).withValues(alpha: 0.18 * t),
                  _glow.withValues(alpha: 0),
                ],
                stops: const [0.0, 0.55, 1.0],
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Three thin rings radiating out from the mark, staggered, fading as
/// they grow — a calm "breath out" rhythm.
class _RippleRings extends StatelessWidget {
  const _RippleRings({required this.animation});

  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, _) => CustomPaint(
        size: const Size(300, 240),
        painter: _RipplePainter(animation.value),
      ),
    );
  }
}

class _RipplePainter extends CustomPainter {
  _RipplePainter(this.t);

  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    if (t == 0) return;
    final center = size.center(Offset.zero);
    for (var i = 0; i < 3; i++) {
      final p = (t + i / 3) % 1.0;
      final eased = Curves.easeOut.transform(p);
      final radius = 80 + 70 * eased;
      final opacity = (1 - p) * 0.35;
      canvas.drawCircle(
        center,
        radius,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.4
          ..color = _ripple.withValues(alpha: opacity),
      );
    }
  }

  @override
  bool shouldRepaint(_RipplePainter oldDelegate) => oldDelegate.t != t;
}

/// "MINDCARE" set live (not from the PNG) so each letter can settle in:
/// the spacing contracts from wide to tight while letters rise and fade in
/// one after another.
class _Wordmark extends StatelessWidget {
  const _Wordmark({required this.animation});

  final Animation<double> animation;

  static const _letters = 'MINDCARE';

  @override
  Widget build(BuildContext context) {
    final style = GoogleFonts.montserrat(
      fontSize: 34,
      fontWeight: FontWeight.w700,
      color: _ink,
      height: 1,
    );

    return AnimatedBuilder(
      animation: animation,
      builder: (context, _) {
        final t = animation.value;
        final spacing = 1.5 + 14 * (1 - t);
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (var i = 0; i < _letters.length; i++)
              _letter(i, t, spacing, style),
          ],
        );
      },
    );
  }

  Widget _letter(int i, double t, double spacing, TextStyle style) {
    // Each letter starts a little after the previous one.
    const stagger = 0.06;
    final local = ((t - i * stagger) / (1 - (_letters.length - 1) * stagger))
        .clamp(0.0, 1.0);
    final last = i == _letters.length - 1;
    return Padding(
      padding: EdgeInsets.only(right: last ? 0 : spacing),
      child: Opacity(
        opacity: local,
        child: Transform.translate(
          offset: Offset(0, 14 * (1 - local)),
          child: Text(_letters[i], style: style),
        ),
      ),
    );
  }
}

class _Tagline extends StatelessWidget {
  const _Tagline({required this.animation});

  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) => Opacity(
        opacity: animation.value,
        child: Transform.translate(
          offset: Offset(0, 8 * (1 - animation.value)),
          child: child,
        ),
      ),
      child: Text(
        'A PATHWAY TO MENTAL WELLBEING',
        style: GoogleFonts.montserrat(
          fontSize: 11.5,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.6,
          color: _ink.withValues(alpha: 0.75),
        ),
      ),
    );
  }
}
