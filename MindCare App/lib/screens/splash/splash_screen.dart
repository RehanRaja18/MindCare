import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

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
  late final AnimationController _progressController;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoOpacity;

  // Same looping clip as the marketing site's hero, bundled so the splash
  // never waits on the network.
  final VideoPlayerController _video = VideoPlayerController.asset(
    'assets/videos/splash_bg.mp4',
    videoPlayerOptions: VideoPlayerOptions(mixWithOthers: true),
  );
  bool _videoReady = false;

  static const _splashDuration = Duration(milliseconds: 3500);

  @override
  void initState() {
    super.initState();

    _entryController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    _logoScale = Tween<double>(begin: 0.85, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.easeOutCubic),
    );
    _logoOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.0, 0.7, curve: Curves.easeOut),
      ),
    );
    _entryController.forward();

    // Subtle "breathing" pulse: a sine wave from a linear repeat, so it
    // starts exactly at scale 1.0 (no jump) and loops with no seam.
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3200),
    )..repeat();

    _progressController = AnimationController(
      vsync: this,
      duration: _splashDuration,
    )..forward();

    _initVideo();

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

  Future<void> _initVideo() async {
    try {
      await _video.initialize();
      // Muted is required for autoplay on web / iOS Safari.
      await _video.setVolume(0);
      await _video.setLooping(true);
      await _video.play();
      if (mounted) setState(() => _videoReady = true);
    } catch (_) {
      // Fall back to the static gradient if the video can't play.
    }
  }

  @override
  void dispose() {
    _entryController.dispose();
    _pulseController.dispose();
    _progressController.dispose();
    _video.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primaryDark,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Base colour shown until the first video frame is ready.
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF2A2320), Color(0xFF111827)],
              ),
            ),
          ),
          AnimatedOpacity(
            opacity: _videoReady ? 1 : 0,
            duration: const Duration(milliseconds: 900),
            curve: Curves.easeOut,
            child: _videoReady ? _CoverVideo(controller: _video) : null,
          ),
          // Warm tint + dark fade so the logo reads on any frame.
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0x66111827),
                  Color(0x33C2410C),
                  Color(0xE6111827),
                ],
                stops: [0.0, 0.5, 1.0],
              ),
            ),
          ),
          Center(
            child: AnimatedBuilder(
              animation: Listenable.merge([_entryController, _pulseController]),
              builder: (context, child) {
                final pulse = 1.0 +
                    0.025 * math.sin(_pulseController.value * 2 * math.pi);
                return Opacity(
                  opacity: _logoOpacity.value,
                  child: Transform.scale(
                    scale: _logoScale.value * pulse,
                    child: child,
                  ),
                );
              },
              child: const _LogoCard(),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 56,
            child: FadeTransition(
              opacity: _logoOpacity,
              child: Center(
                child: SizedBox(
                  width: 120,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(2),
                    child: AnimatedBuilder(
                      animation: _progressController,
                      builder: (context, _) => LinearProgressIndicator(
                        value: Curves.easeInOut
                            .transform(_progressController.value),
                        minHeight: 3,
                        backgroundColor: Colors.white.withValues(alpha: 0.18),
                        valueColor: const AlwaysStoppedAnimation(
                          Color(0xFFFDBA74),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Fills the available space like CSS `object-fit: cover`.
class _CoverVideo extends StatelessWidget {
  const _CoverVideo({required this.controller});

  final VideoPlayerController controller;

  @override
  Widget build(BuildContext context) {
    final size = controller.value.size;
    return ClipRect(
      child: FittedBox(
        fit: BoxFit.cover,
        child: SizedBox(
          width: size.width,
          height: size.height,
          child: VideoPlayer(controller),
        ),
      ),
    );
  }
}

/// Frosted-glass card holding the full-colour logo. The wordmark is dark,
/// so it sits on a light glass panel rather than directly on the video.
class _LogoCard extends StatelessWidget {
  const _LogoCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 40,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(32),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: Container(
            padding: const EdgeInsets.fromLTRB(28, 30, 28, 26),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.82),
              borderRadius: BorderRadius.circular(32),
              border: Border.all(color: Colors.white.withValues(alpha: 0.6)),
            ),
            child: Image.asset(
              'assets/images/mindcare_logo.png',
              width: 190,
              fit: BoxFit.contain,
            ),
          ),
        ),
      ),
    );
  }
}
