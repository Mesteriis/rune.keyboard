# Q7: current API 37 boundary and restart run

At clean source `16c292bd`, an isolated ARM64 API 37 (16 KiB) emulator ran
the Android boundary runner with the pinned llama.cpp submodule, an isolated
ADB server, software-navigation configuration, SwiftShader and the CI Vulkan
feature settings. All three global animation scales were set to zero and read
back. Debug application and test APKs assembled and Rune was selected as the
IME on the disposable emulator.

The boundary runner exited zero and accepted fresh JUnit results for all
scheduled scopes. The general XML contains 363 cases: 315 executed, 48 skipped,
zero failures and zero errors. Its required-case gate includes all nine reviewed
chat protection and manual-selection identities. Seven separately routed
scopes passed 18 cases with no skips: personal (4), case rejection (2),
confirmed words (3), export navigation (1), qualification lifecycle (1),
qualification safety (1) and native runtime (6). The API 26-only export
picker was not scheduled. After rebuilding the ordinary debug APKs, all four
synthetic case-rejection and confirmed-word write/reload restart phases passed.

The first setup attempt was interrupted before any tests because its temporary
orchestration command had an environment-argument error; it is not counted.
During the successful run one editor-action case took several minutes. A
request to signal its process for a stack dump was rejected by Android with
`Operation not permitted`; the process remained alive, the case finished and
the full runner continued. No stack was collected and the reason for the delay
is not established.

This is a local emulator result, not the complete hosted x86_64 workflow,
failure-artifact collection, physical Fold acceptance or evidence for the 48
skipped general cases. The temporary checkout, APKs, emulator, reports and
isolated ADB server were removed. No user phone was changed.
