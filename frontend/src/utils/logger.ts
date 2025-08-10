/**
 * 프론트엔드 로깅 유틸리티
 * 개발/프로덕션 환경에 따른 로그 레벨 관리
 * 구조화된 로그 메시지 제공
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

export interface LogContext {
  component?: string;
  action?: string;
  projectId?: number;
  fileId?: number;
  userId?: string;
  sessionId?: string;
  timestamp?: string;
  [key: string]: any;
}

export class Logger {
  private static instance: Logger;
  private logLevel: LogLevel;
  private isDevelopment: boolean;
  private sessionId: string;

  private constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development';
    this.logLevel = this.isDevelopment ? LogLevel.DEBUG : LogLevel.INFO;
    this.sessionId = this.generateSessionId();
    
    // 세션 시작 로그
    this.info('Logger 초기화됨', { 
      component: 'Logger',
      action: 'initialize',
      environment: process.env.NODE_ENV,
      logLevel: LogLevel[this.logLevel],
      sessionId: this.sessionId
    });
  }

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  private generateSessionId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 5);
    return `${timestamp}-${random}`;
  }

  private formatMessage(level: string, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const ctx = { ...context, sessionId: this.sessionId, timestamp };
    
    if (this.isDevelopment) {
      return `[${timestamp}] [${level}] ${message} ${context ? JSON.stringify(ctx, null, 2) : ''}`;
    } else {
      return `[${level}] ${message} ${context ? JSON.stringify(ctx) : ''}`;
    }
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.logLevel;
  }

  public debug(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.DEBUG)) {
      console.debug(this.formatMessage('DEBUG', message, context));
    }
  }

  public info(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.INFO)) {
      console.log(this.formatMessage('INFO', message, context));
    }
  }

  public warn(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.WARN)) {
      console.warn(this.formatMessage('WARN', message, context));
    }
  }

  public error(message: string, error?: Error | any, context?: LogContext): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      const errorContext = {
        ...context,
        error: error ? {
          name: error.name,
          message: error.message,
          stack: error.stack,
          ...(error.response && {
            status: error.response.status,
            statusText: error.response.statusText,
            data: error.response.data
          })
        } : undefined
      };
      console.error(this.formatMessage('ERROR', message, errorContext));
    }
  }

  // 특정 컴포넌트용 로거 생성
  public createComponentLogger(componentName: string) {
    return {
      debug: (message: string, context?: LogContext) => 
        this.debug(message, { ...context, component: componentName }),
      info: (message: string, context?: LogContext) => 
        this.info(message, { ...context, component: componentName }),
      warn: (message: string, context?: LogContext) => 
        this.warn(message, { ...context, component: componentName }),
      error: (message: string, error?: Error | any, context?: LogContext) => 
        this.error(message, error, { ...context, component: componentName })
    };
  }

  // API 호출 로깅 헬퍼
  public logApiCall(method: string, url: string, context?: LogContext) {
    this.debug(`API 호출: ${method} ${url}`, {
      ...context,
      action: 'api_call',
      method,
      url
    });
  }

  public logApiResponse(method: string, url: string, status: number, duration?: number, context?: LogContext) {
    const message = `API 응답: ${method} ${url} - ${status}`;
    const logContext = {
      ...context,
      action: 'api_response',
      method,
      url,
      status,
      duration
    };

    if (status >= 400) {
      this.error(message, undefined, logContext);
    } else {
      this.debug(message, logContext);
    }
  }

  public logApiError(method: string, url: string, error: any, context?: LogContext) {
    this.error(`API 오류: ${method} ${url}`, error, {
      ...context,
      action: 'api_error',
      method,
      url
    });
  }

  // 사용자 액션 로깅
  public logUserAction(action: string, context?: LogContext) {
    this.info(`사용자 액션: ${action}`, {
      ...context,
      action: 'user_action',
      userAction: action
    });
  }

  // 성능 로깅
  public logPerformance(operation: string, duration: number, context?: LogContext) {
    const message = `성능: ${operation} - ${duration}ms`;
    
    if (duration > 5000) {
      this.warn(message, { ...context, action: 'performance', operation, duration });
    } else {
      this.debug(message, { ...context, action: 'performance', operation, duration });
    }
  }

  // 상태 변경 로깅
  public logStateChange(component: string, stateName: string, oldValue: any, newValue: any, context?: LogContext) {
    this.debug(`상태 변경: ${component}.${stateName}`, {
      ...context,
      component,
      action: 'state_change',
      stateName,
      oldValue: this.sanitizeValue(oldValue),
      newValue: this.sanitizeValue(newValue)
    });
  }

  // 민감한 데이터 필터링
  private sanitizeValue(value: any): any {
    if (typeof value === 'object' && value !== null) {
      const sanitized = { ...value };
      // 비밀번호, 토큰 등 민감한 정보 제거
      const sensitiveKeys = ['password', 'token', 'secret', 'key', 'auth'];
      sensitiveKeys.forEach(key => {
        if (key in sanitized) {
          sanitized[key] = '[REDACTED]';
        }
      });
      return sanitized;
    }
    return value;
  }

  // 로그 레벨 변경 (디버깅용)
  public setLogLevel(level: LogLevel): void {
    this.logLevel = level;
    this.info(`로그 레벨 변경: ${LogLevel[level]}`, { 
      component: 'Logger',
      action: 'setLogLevel',
      level: LogLevel[level]
    });
  }

  // 세션 정보 가져오기
  public getSessionId(): string {
    return this.sessionId;
  }
}

// 전역 로거 인스턴스
export const logger = Logger.getInstance();

// 편의 함수들
export const createComponentLogger = (componentName: string) => 
  logger.createComponentLogger(componentName);

// Hook용 로거
export const useLogger = (componentName: string) => {
  return logger.createComponentLogger(componentName);
};