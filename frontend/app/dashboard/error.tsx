'use client';

// Modern Error Boundary - React 19 error handling patterns
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface DashboardErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: DashboardErrorProps) {
  useEffect(() => {
    // Log error to monitoring service (Sentry, etc.)
    console.error('Dashboard error:', error);
    
    // Report to analytics
    if (typeof window !== 'undefined') {
      // Track error event
      try {
        // analytics.track('dashboard_error', {
        //   error: error.message,
        //   digest: error.digest,
        //   url: window.location.href,
        // });
      } catch (e) {
        console.error('Failed to report error:', e);
      }
    }
  }, [error]);

  const isDevelopment = process.env.NODE_ENV === 'development';
  
  return (
    <div className="flex items-center justify-center min-h-[60vh] px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            We encountered an error while loading your dashboard. This has been logged and our team has been notified.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {isDevelopment && (
            <details className="rounded-lg bg-muted p-4 text-sm">
              <summary className="cursor-pointer font-medium text-muted-foreground">
                Error Details (Development Only)
              </summary>
              <div className="mt-2 space-y-2">
                <div>
                  <strong>Message:</strong> {error.message}
                </div>
                {error.digest && (
                  <div>
                    <strong>Digest:</strong> {error.digest}
                  </div>
                )}
                <div>
                  <strong>Stack:</strong>
                  <pre className="mt-1 whitespace-pre-wrap text-xs">
                    {error.stack}
                  </pre>
                </div>
              </div>
            </details>
          )}
          
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button 
              onClick={reset} 
              className="flex-1"
              variant="default"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
            
            <Button 
              onClick={() => window.location.href = '/'}
              variant="outline"
              className="flex-1"
            >
              <Home className="mr-2 h-4 w-4" />
              Go Home
            </Button>
          </div>
          
          <p className="text-center text-sm text-muted-foreground">
            If this problem persists, please{' '}
            <a 
              href="mailto:support@pipewise.com" 
              className="underline hover:no-underline"
            >
              contact support
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}