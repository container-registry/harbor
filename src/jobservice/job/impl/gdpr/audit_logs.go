package gdpr

import (
	"fmt"
	"github.com/goharbor/harbor/src/jobservice/job"
	"github.com/goharbor/harbor/src/lib/errors"
	"github.com/goharbor/harbor/src/pkg/audit"
)

const UserNameParam = "username"

type AuditLogsCleanup struct {
	manager audit.Manager
}

func (a AuditLogsCleanup) MaxFails() uint {
	return 3
}

func (a AuditLogsCleanup) MaxCurrency() uint {
	return 1
}

func (a AuditLogsCleanup) ShouldRetry() bool {
	return true
}

func (a AuditLogsCleanup) Validate(params job.Parameters) error {
	if params == nil {
		// Params are required
		return errors.New("missing job parameters")
	}
	_, err := a.parseParams(params)
	return err
}

func (a *AuditLogsCleanup) init() {
	if a.manager == nil {
		a.manager = audit.New()
	}
}

func (a AuditLogsCleanup) Run(ctx job.Context, params job.Parameters) error {
	logger := ctx.GetLogger()
	logger.Info("GDPR compliant audit logs cleanup job start")
	logger.Infof("job parameters %+v", params)
	a.init()
	username, err := a.parseParams(params)
	if err != nil {
		return err
	}
	return a.manager.MakeGDPRCompliant(ctx.SystemContext(), username)
}

func (a AuditLogsCleanup) parseParams(params job.Parameters) (string, error) {
	value, exist := params[UserNameParam]
	if !exist {
		return "", fmt.Errorf("param %s not found", UserNameParam)
	}
	str, ok := value.(string)
	if !ok {
		return "", fmt.Errorf("the value of %s isn't string", UserNameParam)
	}
	fmt.Println("cleaning up logs for a user", str)
	return str, nil
}
