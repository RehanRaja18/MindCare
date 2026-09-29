import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../main.dart';
import '../onboarding/welcome_screen.dart';

// Same cream as the Welcome screen and the web front page, so the hand-off
// from splash to Welcome is seamless.
const _cream = Color(0xFFF5F0E8);
const _ink = Color(0xFF111827);

const _easeOutQuint = Cubic(0.22, 1, 0.36, 1);

// The mark is split into layers by tool/split_logo.ps1: the orange figure
// and the teal/tan ring. mark_full is the untouched artwork the two settle
// into.
const _figureAsset = 'assets/images/splash/mark_figure.png';
const _ringAsset = 'assets/images/splash/mark_ring.png';
const _fullAsset = 'assets/images/splash/mark_full.png';
const _soundAsset = 'sounds/splash_intro.wav';

// Stage geometry. The mark (522×538 artwork) is drawn at [_markW] wide in
// the middle of a square stage large enough for the ribbon to swirl
// beyond it. Ring centre/radius are measured from the artwork.
const _stage = 300.0;
const _markW = 180.0;
const _markH = _markW * 538 / 522;
const _markLeft = (_stage - _markW) / 2;
const _markTop = (_stage - _markH) / 2;
const _ringCenter = Offset(_markLeft + 0.498 * _markW, _markTop + 0.513 * _markH);
const _ringRadius = 0.40 * _markW;

/// Splash: plain background, all the motion lives in the logo.
///  1. the figure springs up out of nothing,
///  2. a teal-to-tan ribbon spirals up around it like a helix,
///  3. the helix unwinds and coils into the ring, which locks in with a
///     soft pulse and a sheen,
///  4. MINDCARE settles letter by letter, then the tagline.
/// A synthesised sound (assets/sounds/splash_intro.wav) is timed to it.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  static const _entrySeconds = 3.8;
  static const _handOff = Duration(milliseconds: 4900);

  late final AnimationController _entry = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: (_entrySeconds * 1000).round()),
  );

  late final AnimationController _breathe = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3200),
  );

  // Phases, in seconds on the entry timeline.
  late final _figureIn = _interval(0.0, 0.9, Curves.easeOutBack);
  late final _grow = _interval(0.35, 1.35, Curves.easeInOutCubic);
  late final _coil = _interval(1.25, 2.05, Curves.easeInOutCubic);
  late final _ringIn = _interval(1.95, 2.25, Curves.easeOut);
  late final _settle = _interval(2.35, 2.6, Curves.easeOut);
  late final _lockPulse = _interval(2.0, 2.5, Curves.linear);
  late final _sheen = _interval(2.2, 2.95, Curves.easeInOut);
  late final _word = _interval(2.45, 3.4, _easeOutQuint);
  late final _tagline = _interval(3.0, 3.8, Curves.easeOut);

  Timer? _handOffTimer;

  @override
  void initState() {
    super.initState();
    _entry.forward();
    _SplashSound.play();

    Future.delayed(const Duration(milliseconds: 3000), () {
      if (mounted) _breathe.repeat();
    });

    _handOffTimer = Timer(_handOff, () {
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
    _handOffTimer?.cancel();
    _entry.dispose();
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
              width: _stage,
              height: _stage,
              child: AnimatedBuilder(
                animation: Listenable.merge([_entry, _breathe]),
                builder: (context, _) => _buildStage(),
              ),
            ),
            _Wordmark(animation: _word),
            const SizedBox(height: 10),
            _Tagline(animation: _tagline),
          ],
        ),
      ),
    );
  }

  Widget _buildStage() {
    final seconds = _entry.value * _entrySeconds;
    // Ribbon keeps spinning around the figure until it has coiled.
    final spin = seconds * 2 * math.pi * 0.55;
    final ribbon = _RibbonState(
      grow: _grow.value,
      coil: _coil.value,
      spin: spin,
      opacity: 1 - _ringIn.value,
    );

    // A quick "lock" bump when the ring snaps in, then a slow breath.
    final pulse = math.sin(_lockPulse.value * math.pi) * 0.06;
    final breath = 0.02 * math.sin(_breathe.value * 2 * math.pi);
    final markScale = 1 + pulse + breath;

    final f = _figureIn.value;
    final figureBlur = 10 * (1 - f).clamp(0.0, 1.0);

    Widget figure = Image.asset(_figureAsset, width: _markW, height: _markH);
    if (figureBlur > 0.05) {
      figure = ImageFiltered(
        imageFilter: ImageFilter.blur(sigmaX: figureBlur, sigmaY: figureBlur),
        child: figure,
      );
    }
    figure = Opacity(
      opacity: f.clamp(0.0, 1.0),
      child: Transform.rotate(
        angle: -0.45 * (1 - f),
        child: Transform.scale(scale: 0.3 + 0.7 * f, child: figure),
      ),
    );

    final ringIn = _ringIn.value;
    final ring = Opacity(
      opacity: ringIn,
      child: Transform.scale(
        scale: 1.02 - 0.02 * ringIn,
        child: Image.asset(_ringAsset, width: _markW, height: _markH),
      ),
    );

    // Once settled, swap the two layers for the untouched artwork so the
    // final frame is pixel-exact.
    final settle = _settle.value;
    final layered = Opacity(
      opacity: 1 - settle,
      child: Stack(children: [ring, figure]),
    );
    final full = Opacity(
      opacity: settle,
      child: Image.asset(_fullAsset, width: _markW, height: _markH),
    );

    final mark = _Sheen(
      progress: _sheen.value,
      child: SizedBox(
        width: _markW,
        height: _markH,
        child: Stack(children: [layered, full]),
      ),
    );

    return Stack(
      clipBehavior: Clip.none,
      children: [
        // Burst ring when the ribbon locks in.
        Positioned.fill(
          child: CustomPaint(painter: _LockBurstPainter(_lockPulse.value)),
        ),
        // Ribbon behind the figure...
        Positioned.fill(
          child: CustomPaint(painter: _RibbonPainter(ribbon, front: false)),
        ),
        Positioned(
          left: _markLeft,
          top: _markTop,
          child: Transform.scale(scale: markScale, child: mark),
        ),
        // ...and in front of it, so it reads as wrapping around.
        Positioned.fill(
          child: CustomPaint(painter: _RibbonPainter(ribbon, front: true)),
        ),
      ],
    );
  }
}

/// Plays the splash sound once. Kept outside the widget so the tail of the
/// sound isn't cut off when the splash is replaced by the Welcome screen.
/// Uses the "ambient" audio session on iOS, so it respects the silent switch
/// and never interrupts music the user is already playing.
class _SplashSound {
  static AudioPlayer? _player;

  static Future<void> play() async {
    try {
      final player = _player ??= AudioPlayer();
      player.onPlayerComplete.first.then((_) {
        player.dispose();
        _player = null;
      });
      await player.play(
        AssetSource(_soundAsset),
        volume: 0.8,
        ctx: AudioContextConfig(respectSilence: true).build(),
      );
    } catch (_) {
      // Browsers may block sound before the user has interacted with the
      // page; the animation carries on silently.
    }
  }
}

class _RibbonState {
  const _RibbonState({
    required this.grow,
    required this.coil,
    required this.spin,
    required this.opacity,
  });

  /// How much of the ribbon has been drawn (0 → 1).
  final double grow;

  /// 0 = helix around the figure, 1 = lying exactly on the ring.
  final double coil;

  /// Rotation of the helix around its vertical axis.
  final double spin;

  final double opacity;
}

/// A twisting ribbon drawn as many short round-capped strokes. Each point
/// is a blend between a helix around the figure and the logo's ring, so as
/// [_RibbonState.coil] goes 0 → 1 the helix unwinds into the ring. Depth
/// (z) decides whether a segment is behind or in front of the figure and
/// shades it, which sells the 3D wrap.
class _RibbonPainter extends CustomPainter {
  _RibbonPainter(this.s, {required this.front});

  final _RibbonState s;
  final bool front;

  static const _segments = 150;
  static const _width = 15.0;
  static const _turns = 1.6;

  // Teal → charcoal → teal → tan, sampled from the logo's ring.
  static const _stops = [0.0, 0.4, 0.7, 1.0];
  static const _colors = [
    Color(0xFF3E7F86),
    Color(0xFF2E3A40),
    Color(0xFF4A8C8F),
    Color(0xFFC99A6A),
  ];

  static Color _colorAt(double u) {
    for (var i = 0; i < _stops.length - 1; i++) {
      if (u <= _stops[i + 1]) {
        final t = (u - _stops[i]) / (_stops[i + 1] - _stops[i]);
        return Color.lerp(_colors[i], _colors[i + 1], t)!;
      }
    }
    return _colors.last;
  }

  /// Returns (x, y, z) for position [u] along the ribbon.
  (Offset, double, double) _point(double u) {
    // Helix: rises from below the mark to above it, wrapping the figure.
    final theta = u * _turns * 2 * math.pi + s.spin;
    final helixY = lerpDouble(_stage - 30, 40, u)!;
    const helixR = 60.0;
    final helix = Offset(_ringCenter.dx + helixR * math.cos(theta), helixY);
    final helixZ = math.sin(theta);

    // Ring: starts at the bottom and goes all the way round.
    final alpha = math.pi / 2 + 2 * math.pi * u;
    final ring = _ringCenter +
        Offset(_ringRadius * math.cos(alpha), _ringRadius * math.sin(alpha));

    final k = s.coil;
    final p = Offset.lerp(helix, ring, k)!;
    final z = lerpDouble(helixZ, 1, k)!;
    // Wide when facing us, narrow edge-on at the sides; flat once coiled.
    final twist = 0.35 + 0.65 * math.sin(theta).abs();
    final w = _width * lerpDouble(twist, 1, k)!;
    return (p, z, w);
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (s.grow <= 0 || s.opacity <= 0) return;

    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final head = s.grow;
    var (prev, _, _) = _point(0);
    for (var i = 1; i <= _segments; i++) {
      final u = head * i / _segments;
      final (p, z, w) = _point(u);
      if ((z >= 0) == front) {
        var c = _colorAt(u);
        c = z >= 0
            ? Color.lerp(c, Colors.white, 0.18 * z * (1 - s.coil))!
            : Color.lerp(c, Colors.black, 0.35 * -z)!;
        // The trailing end fades in, so the ribbon feels like it's being
        // pulled out of the air rather than starting with a hard edge.
        final tail = (u / 0.03).clamp(0.0, 1.0);
        paint
          ..strokeWidth = w
          ..color = c.withValues(alpha: s.opacity * tail);
        canvas.drawLine(prev, p, paint);
      }
      prev = p;
    }

    // Soft glowing spark at the leading end while it's still travelling.
    if (front && s.coil < 1) {
      final (tip, _, _) = _point(head);
      final glow = (1 - s.coil) * s.opacity;
      canvas.drawCircle(
        tip,
        16,
        Paint()
          ..shader = RadialGradient(
            colors: [
              Colors.white.withValues(alpha: 0.85 * glow),
              const Color(0xFFFDBA74).withValues(alpha: 0.35 * glow),
              const Color(0x00FDBA74),
            ],
          ).createShader(Rect.fromCircle(center: tip, radius: 16)),
      );
    }
  }

  @override
  bool shouldRepaint(_RibbonPainter old) =>
      old.s.grow != s.grow ||
      old.s.coil != s.coil ||
      old.s.spin != s.spin ||
      old.s.opacity != s.opacity;
}

/// One expanding ring + warm flash at the moment the ring locks in.
class _LockBurstPainter extends CustomPainter {
  _LockBurstPainter(this.t);

  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    if (t <= 0 || t >= 1) return;
    final eased = Curves.easeOut.transform(t);
    canvas.drawCircle(
      _ringCenter,
      _ringRadius + 70 * eased,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5 * (1 - t) + 0.5
        ..color = const Color(0xFFFB923C).withValues(alpha: 0.45 * (1 - t)),
    );
    canvas.drawCircle(
      _ringCenter,
      _ringRadius * 1.4,
      Paint()
        ..shader = RadialGradient(
          colors: [
            const Color(0xFFFDBA74).withValues(alpha: 0.35 * (1 - eased)),
            const Color(0x00FDBA74),
          ],
        ).createShader(
          Rect.fromCircle(center: _ringCenter, radius: _ringRadius * 1.4),
        ),
    );
  }

  @override
  bool shouldRepaint(_LockBurstPainter old) => old.t != t;
}

/// A diagonal band of light sweeping across the mark once it's complete.
class _Sheen extends StatelessWidget {
  const _Sheen({required this.progress, required this.child});

  final double progress;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (progress <= 0 || progress >= 1) return child;
    return ShaderMask(
      blendMode: BlendMode.srcATop,
      shaderCallback: (bounds) {
        final x = lerpDouble(-bounds.width, bounds.width * 1.6, progress)!;
        return LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: 0.55),
            Colors.white.withValues(alpha: 0),
          ],
          stops: const [0.35, 0.5, 0.65],
        ).createShader(
          Rect.fromLTWH(x - bounds.width / 2, 0, bounds.width, bounds.height),
        );
      },
      child: child,
    );
  }
}

/// "MINDCARE" set live so each letter can settle in: spacing contracts from
/// wide to tight while letters rise and fade in one after another.
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
        // Scales down only if the spaced-out word is wider than the screen.
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (var i = 0; i < _letters.length; i++)
                  _letter(i, t, spacing, style),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _letter(int i, double t, double spacing, TextStyle style) {
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
