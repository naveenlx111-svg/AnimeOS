#version 440

// Unpacks the side-by-side colour|alpha video and dissolves it away.
//
// The dissolve is not a global fade. A global fade drops the whole storm's
// opacity together, which reads as a pink sheet going see-through. Instead the
// cut-off is raised per pixel against a noise field, so individual petals wink
// out at their own moments and the gaps between them open and grow -- the
// desktop appears through holes in the storm rather than behind a veil.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float progress;     // 0 at full storm, 1 when nothing is left
    float noiseScale;
    float grain;        // how uneven the dissolve is; 0 == uniform fade
    float tintAmount;
    vec4 tint;
};

layout(binding = 1) uniform sampler2D source;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

// Value noise: cheap, and smooth enough that the holes read as drifting
// clearings rather than as static.
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x),
               mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void main() {
    // The two halves share one texture, so stay a hair off the seam: chroma
    // subsampling bleeds colour across x = 0.5 and it would tint the matte.
    float x = clamp(qt_TexCoord0.x, 0.001, 0.999) * 0.5;
    vec3 rgb = texture(source, vec2(x, qt_TexCoord0.y)).rgb;
    float a = texture(source, vec2(x + 0.5, qt_TexCoord0.y)).r;

    float n = noise(qt_TexCoord0 * noiseScale)
            + 0.5 * noise(qt_TexCoord0 * noiseScale * 2.7);
    n /= 1.5;

    // Each pixel gets its own threshold. Early on only the faintest haze is
    // below it; by the end even the solid petals have been passed.
    float cut = progress * (1.0 + grain) - grain * n;
    float alpha = clamp((a - cut) / max(1.0 - cut, 0.08), 0.0, 1.0);

    // Raising the cut-off keeps only the petals' near-white hot cores, so the
    // storm drifts colourless exactly as it thins. Push what survives back
    // toward the blossom pink, harder the further the dissolve has gone.
    float lum = dot(rgb, vec3(0.2126, 0.7152, 0.0722));
    rgb = mix(rgb, vec3(lum) * tint.rgb, progress * tintAmount);

    // Premultiplied: Qt composites scene-graph nodes that way, and these
    // petals are emissive, so premultiplied is also what they physically are.
    fragColor = vec4(rgb * alpha, alpha) * qt_Opacity;
}
