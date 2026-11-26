# U9: live IME PixelCopy upper-bound observation

`EmojiPresentedFrameInstrumentedTest` exercises the actual debug IME and a
separate-process public QA editor on a task-owned API 26 ARM64 emulator with
2 GiB RAM. It opens Symbols, obtains the IME window and first copies that surface
as a negative control. The central region contains no yellow emoji-grid pixels
in that state. It then injects explicit down/up events on the observed Emoji key
and requests PixelCopy frames until the central region contains at least 500
yellow pixels. It also verifies the native GridView is present. This is a
measurement-validity test, not an assertion that the performance budget passes.

In five sequential instrumentation invocations, with the target package
force-stopped before each, the negative control was zero yellow pixels; each
positive copy had 37,672 and required two copy requests. The elapsed time from
before injection to the completion callback for the first positive copied
buffer was 32.890, 41.542, 31.683, 40.820 and 42.194 ms, median 40.820 ms.
All five were below 50 ms. The pixel scan that identifies the positive copy runs
after the callback and is not part of the reported elapsed time; scans of prior
copies and all injection, copy and callback overhead before the positive callback
are included. This bounds when a suitable buffer was copied; it is not a
SurfaceFlinger presentation timestamp or proof of physical display latency.
The five samples are from one emulator, with instrumentation and warm filesystem
caches, and cannot establish a release/profile build or Fold budget.

The initial two calibration runs failed their negative control because the
region included the yellow Emoji key on the Symbols layer. The final region
excludes that row. A subsequent five-run calibration using `UiDevice.click`
observed 138–151 ms including the driver's higher-level click overhead. Those
runs are retained as diagnostics, not silently removed from a performance gate.
The final method uses explicit pointer down/up and a callback timestamp.

The four existing real-IME emoji functional tests passed on the same isolated
emulator; debug/test builds and `lintDebug` passed. Source before the new test:
`5a8851c5da35117f74c93884af73549b93819d9f`; main APK SHA-256
`4ec78729849a0d86bed2e9636c1717e859692e86836a6f2e98ef075ed1af82f3`;
new test source SHA-256
`c62797132975d846e72da0a773e9cd2b8756d77f83ac20c4105885d625c1dd06`;
test APK SHA-256
`8956423a62e75cb27bccaf39863e5a4ee8a92dc47a9e19a647da2085722cd804`.
Installed bytes matched both APKs. Raw build, failed calibration, functional and
final run logs are under `build/review-u9-pixelcopy/`. The emulator was stopped;
Fold was not used. Actual first-frame presentation, release-like performance,
baseline cold-start comparison, Fold and manual TalkBack remain open.
