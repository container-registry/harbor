package main

import (
	"context"
	"dagger/harbor/internal/dagger"
	"fmt"
	"log"
	"strings"
)

const (
	GOLANGCILINT_VERSION = "v1.61.0"
	GO_VERSION           = "latest"
	SYFT_VERSION         = "v1.9.0"
	GORELEASER_VERSION   = "v2.3.2"
)

var (
	SupportedPlatforms = []string{"linux/arm64", "linux/amd64"}
	packages           = []string{"core", "jobservice", "registryctl", "cmd/exporter", "cmd/standalone-db-migrator"}
	//packages = []string{"core", "jobservice"}
)

type BuildMetadata struct {
	Package    string
	BinaryPath string
	Container  *dagger.Container
	Platform   string
}

func New(
	// Local or remote directory with source code, defaults to "./"
	// +optional
	// +defaultPath="./"
	source *dagger.Directory,
) *Harbor {
	return &Harbor{Source: source}
}

type Harbor struct {
	Source *dagger.Directory
}

func (m *Harbor) BuildImages(ctx context.Context,
	// +optional
	// +default=["linux/arm64","linux/amd64"]
	platforms []string,
	// +optional
	// +default=["core", "jobservice", "registryctl", "cmd/exporter", "cmd/standalone-db-migrator"]
	packages []string) []*dagger.Container {
	var images []*dagger.Container
	for _, platform := range platforms {
		for _, pkg := range packages {
			img := m.buildImage(ctx, platform, pkg)
			images = append(images, img)
		}
	}
	return images
}

func (m *Harbor) buildImage(ctx context.Context, platform string, pkg string) *dagger.Container {
	bc := m.buildBinary(ctx, platform, pkg)
	img := dag.Container(dagger.ContainerOpts{Platform: dagger.Platform(platform)}).
		WithFile("/"+pkg, bc.Container.File(bc.BinaryPath)).
		WithEntrypoint([]string{"/" + pkg})
	return img
}

func (m *Harbor) buildBinary(ctx context.Context, platform string, pkg string) *BuildMetadata {

	os, arch, err := parsePlatform(platform)
	if err != nil {
		log.Fatalf("Error parsing platform: %v", err)
	}

	outputPath := fmt.Sprintf("bin/%s/%s", platform, pkg)
	src := fmt.Sprintf("%s/main.go", pkg)
	builder := dag.Container().
		From("golang:latest").
		WithMountedCache("/go/pkg/mod", dag.CacheVolume("go-mod-"+GO_VERSION)).
		WithEnvVariable("GOMODCACHE", "/go/pkg/mod").
		WithMountedCache("/go/build-cache", dag.CacheVolume("go-build-"+GO_VERSION)).
		WithEnvVariable("GOCACHE", "/go/build-cache").
		WithMountedDirectory("/harbor", m.Source). // Ensure the source directory with go.mod is mounted
		WithWorkdir("/harbor/src/").
		WithEnvVariable("GOOS", os).
		WithEnvVariable("GOARCH", arch).
		WithEnvVariable("CGO_ENABLED", "0").
		WithExec([]string{"go", "build", "-o", outputPath, "-ldflags", "-extldflags=-static -s -w", src})

	return &BuildMetadata{
		Package:    pkg,
		BinaryPath: outputPath,
		Container:  builder,
		Platform:   platform,
	}
}

func (m *Harbor) buildPortal(ctx context.Context, platform string, pkg string) *dagger.Directory {
	fmt.Println("🛠️  Building Harbor Core...")
	// Define the path for the binary output
	os, arch, err := parsePlatform(platform)

	if err != nil {
		log.Fatalf("Error parsing platform: %v", err)
	}

	outputPath := fmt.Sprintf("bin/%s/%s", platform, pkg)
	src := fmt.Sprintf("src/%s/main.go", pkg)
	builder := dag.Container().
		From("golang:latest").
		WithMountedCache("/go/pkg/mod", dag.CacheVolume("go-mod-"+GO_VERSION)).
		WithEnvVariable("GOMODCACHE", "/go/pkg/mod").
		WithMountedCache("/go/build-cache", dag.CacheVolume("go-build-"+GO_VERSION)).
		WithEnvVariable("GOCACHE", "/go/build-cache").
		WithMountedDirectory("/harbor", m.Source). // Ensure the source directory with go.mod is mounted
		WithWorkdir("/harbor").
		WithEnvVariable("GOOS", os).
		WithEnvVariable("GOARCH", arch).
		WithExec([]string{"go", "build", "-o", outputPath, src})
	return builder.Directory(outputPath)
}

func parsePlatform(platform string) (string, string, error) {
	parts := strings.Split(platform, "/")
	if len(parts) != 2 {
		return "", "", fmt.Errorf("invalid platform format: %s. Should be os/arch. E.g. darwin/amd64", platform)
	}
	return parts[0], parts[1], nil
}
