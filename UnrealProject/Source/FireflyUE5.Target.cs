// Copyright (c) 2026 balalexv. MIT License.

using UnrealBuildTool;
using System.Collections.Generic;

public class FireflyUE5Target : TargetRules
{
	public FireflyUE5Target(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("FireflyUE5");
	}
}
