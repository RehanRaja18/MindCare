import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../main.dart';
import '../onboarding/welcome_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _entryController;
  late final AnimationController _pulseController;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoOpacity;

  @override
  void initState() {
    super.initState();

    _entryController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _logoScale = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.easeOutBack),
    );
    _logoOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.0, 0.6, curve: Curves.easeOut),
      ),
    );
    _entryController.forward();

    // Continuous "breathing" pulse: a sine wave from a linear repeat, so it
    // starts exactly at scale 1.0 (no jump) and loops with no seam.
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat();

    Future.delayed(const Duration(seconds: 3), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          transitionDuration: const Duration(milliseconds: 600),
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

  @override
  void dispose() {
    _entryController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const _AuroraBackground(),
          Center(
            child: AnimatedBuilder(
              animation: Listenable.merge([_entryController, _pulseController]),
              builder: (context, _) {
                final pulse =
                    1.0 + 0.07 * math.sin(_pulseController.value * 2 * math.pi);
                return Opacity(
                  opacity: _logoOpacity.value,
                  child: Transform.scale(
                    scale: _logoScale.value * pulse,
                    child: Image.asset(
                      'assets/images/mindcare_logo.png',
                      width: 220,
                      fit: BoxFit.contain,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Whole-screen warm aurora, mirroring the marketing site's flowing
/// background: two layers of oversized, blurred color blobs, each
/// layer drifting as one piece (translate + scale + rotate) along an
/// uneven, multi-stop path so the motion never reads as a simple
/// back-and-forth loop. Small per-blob jitter is imperceptible once
/// blurred at this scale — moving the whole cluster is what actually
/// reads as motion.
class _AuroraBackground extends StatefulWidget {
  const _AuroraBackground();

  @override
  State<_AuroraBackground> createState() => _AuroraBackgroundState();
}

class _AuroraBackgroundState extends State<_AuroraBackground>
    with TickerProviderStateMixin {
  late final AnimationController _layerA;
  late final AnimationController _layerB;

  @override
  void initState() {
    super.initState();
    _layerA = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 32),
    )..repeat(reverse: true);
    _layerB = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 44),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _layerA.dispose();
    _layerB.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Uses the actual incoming constraints, not MediaQuery.sizeOf — on wide
    // (desktop/web) viewports the app is visually pinned to a fixed-width
    // phone frame (see MobileFrame in main.dart) narrower than the window,
    // and MediaQuery would report the full window size instead.
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = constraints.biggest;

        return Stack(
          children: [
            AnimatedBuilder(
              animation: _layerA,
              builder: (context, _) => _AuroraLayer(
                t: _layerA.value,
                size: size,
                opacity: 0.6,
                stops: const [0, 0.33, 0.66, 1.0],
                dxPercent: const [0, -6, 5, -4],
                dyPercent: const [0, 5, -4, -6],
                scale: const [1, 1.12, 0.95, 1.05],
                rotateDeg: const [0, 6, -5, 4],
                blobs: const [
                  _AuroraBlob(Alignment(-0.56, -0.44), 0.42, Color(0xFFFDBA74)),
                  _AuroraBlob(Alignment(0.56, -0.64), 0.42, Color(0xFFFDA4AF)),
                  _AuroraBlob(Alignment(0.10, 0.64), 0.42, Color(0xFFFCD34D)),
                  _AuroraBlob(Alignment(0.76, 0.44), 0.38, Color(0xFFF0ABFC)),
                ],
              ),
            ),
            AnimatedBuilder(
              animation: _layerB,
              builder: (context, _) => _AuroraLayer(
                t: _layerB.value,
                size: size,
                opacity: 0.35,
                stops: const [0, 0.5, 1.0],
                dxPercent: const [0, 6, -5],
                dyPercent: const [0, 6, 3],
                scale: const [1.05, 0.92, 1.08],
                rotateDeg: const [0, -6, 5],
                blobs: const [
                  _AuroraBlob(Alignment(0.36, 0.10), 0.38, Color(0xFF6EE7B7)),
                  _AuroraBlob(Alignment(-0.70, 0.40), 0.40, Color(0xFFFB923C)),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _AuroraLayer extends StatelessWidget {
  const _AuroraLayer({
    required this.t,
    required this.size,
    required this.opacity,
    required this.stops,
    required this.dxPercent,
    required this.dyPercent,
    required this.scale,
    required this.rotateDeg,
    required this.blobs,
  });

  final double t;
  final Size size;
  final double opacity;
  final List<double> stops;
  final List<double> dxPercent;
  final List<double> dyPercent;
  final List<double> scale;
  final List<double> rotateDeg;
  final List<_AuroraBlob> blobs;

  double _interp(List<double> values) {
    for (var i = 0; i < stops.length - 1; i++) {
      if (t <= stops[i + 1] || i == stops.length - 2) {
        final local = ((t - stops[i]) / (stops[i + 1] - stops[i])).clamp(
          0.0,
          1.0,
        );
        final eased = Curves.easeInOut.transform(local);
        return lerpDouble(values[i], values[i + 1], eased)!;
      }
    }
    return values.last;
  }

  @override
  Widget build(BuildContext context) {
    // Layer is oversized (130% of the viewport, like the web's `inset: -15%`)
    // so it can drift and rotate without ever exposing an edge.
    final layerW = size.width * 1.3;
    final layerH = size.height * 1.3;
    final dxPx = _interp(dxPercent) / 100 * layerW;
    final dyPx = _interp(dyPercent) / 100 * layerH;
    final s = _interp(scale);
    final rotRad = _interp(rotateDeg) * math.pi / 180;

    return Center(
      child: Transform(
        alignment: Alignment.center,
        transform: Matrix4.identity()
          ..translateByDouble(dxPx, dyPx, 0, 1)
          ..scaleByDouble(s, s, s, 1)
          ..rotateZ(rotRad),
        child: Opacity(
          opacity: opacity,
          child: ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: 45, sigmaY: 45),
            child: SizedBox(
              width: layerW,
              height: layerH,
              child: Stack(
                children: [
                  for (final blob in blobs)
                    Align(
                      alignment: blob.alignment,
                      child: Container(
                        width: layerW * blob.radiusFraction * 2,
                        height: layerW * blob.radiusFraction * 2,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              blob.color,
                              blob.color.withValues(alpha: 0.0),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _AuroraBlob {
  const _AuroraBlob(this.alignment, this.radiusFraction, this.color);

  final Alignment alignment;
  final double radiusFraction;
  final Color color;
}
