# Info.plist keys every Slipway app sets explicitly

Missing any of these has cost a rejected upload or a store round trip. Set them in the project
from day one, and check the **archived** Info.plist (inside `App.xcarchive/Products/Applications/
<App>.app/Info.plist`), not just the source file, because build variables are filled in at archive
time.

| Key | Value | Why |
|---|---|---|
| `CFBundlePackageType` | `APPL` | Some generated projects omit it. The archive and device install still work, but Apple's processing fails the upload with ITMS-90183 |
| `CFBundleDisplayName` | Your Home Screen name, with spaces as intended | Otherwise the product or target name is used (e.g. `ExampleCounter` instead of `Example Counter`) |
| `CFBundleShortVersionString` | `$(MARKETING_VERSION)`, e.g. `1.0.0` | Must equal the version in App Store Connect exactly. `1.0` ≠ `1.0.0` |
| `CFBundleVersion` | `$(CURRENT_PROJECT_VERSION)` | Unique per upload. Never reuse a build number |
| `ITSAppUsesNonExemptEncryption` | `false` (if you use no encryption, or only exempt HTTPS) | Skips the export-compliance question on every build |
| `UISupportedInterfaceOrientations` | Exactly what the app supports | Screenshots must match. Landscape apps need landscape screenshots |
| `NS…UsageDescription` | One plain sentence for each permission | Vague purpose strings are a common rejection |
| `UILaunchScreen` | `{}` or a launch storyboard | Needed for full-screen layout on current iPhones |

XcodeGen example (`project.yml`):

```yaml
targets:
  ExampleCounter:
    type: application
    platform: iOS
    deploymentTarget: "17.0"
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.example.counter
        MARKETING_VERSION: 1.0.0
        CURRENT_PROJECT_VERSION: 1
        INFOPLIST_KEY_CFBundleDisplayName: "Example Counter"
        CODE_SIGN_STYLE: Automatic
    info:
      path: Sources/Info.plist
      properties:
        CFBundlePackageType: APPL
        CFBundleDisplayName: Example Counter
        CFBundleShortVersionString: $(MARKETING_VERSION)
        CFBundleVersion: $(CURRENT_PROJECT_VERSION)
        ITSAppUsesNonExemptEncryption: false
        UILaunchScreen: {}
        UISupportedInterfaceOrientations: [UIInterfaceOrientationPortrait]
```

Also add a unit test that reads `Bundle.main.infoDictionary` and asserts the display name and
package type, so a project regeneration can't silently drop them.
