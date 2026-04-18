// Copyright (c) 2026 balalexv. MIT License.

using UnrealBuildTool;
using System.Collections.Generic;

public class FireflyUE5EditorTarget : TargetRules
{
	public FireflyUE5EditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V6;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("FireflyUE5");
	}
}
