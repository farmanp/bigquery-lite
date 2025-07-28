//! Utility functions for the BlazeQueryEngine

use std::time::{Duration, Instant};

/// Format bytes into human-readable string
pub fn format_bytes(bytes: u64) -> String {
    const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
    const THRESHOLD: f64 = 1024.0;
    
    if bytes == 0 {
        return "0 B".to_string();
    }
    
    let mut size = bytes as f64;
    let mut unit_index = 0;
    
    while size >= THRESHOLD && unit_index < UNITS.len() - 1 {
        size /= THRESHOLD;
        unit_index += 1;
    }
    
    format!("{:.2} {}", size, UNITS[unit_index])
}

/// Format duration into human-readable string
pub fn format_duration(duration: Duration) -> String {
    let total_ms = duration.as_millis();
    
    if total_ms < 1000 {
        format!("{}ms", total_ms)
    } else if total_ms < 60_000 {
        format!("{:.2}s", total_ms as f64 / 1000.0)
    } else {
        let minutes = total_ms / 60_000;
        let seconds = (total_ms % 60_000) as f64 / 1000.0;
        format!("{}m {:.2}s", minutes, seconds)
    }
}

/// Performance metrics tracker
pub struct PerformanceTracker {
    start_time: Instant,
    checkpoints: Vec<(String, Instant)>,
}

impl PerformanceTracker {
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            checkpoints: Vec::new(),
        }
    }
    
    pub fn checkpoint(&mut self, name: impl Into<String>) {
        self.checkpoints.push((name.into(), Instant::now()));
    }
    
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }
    
    pub fn report(&self) -> String {
        let mut report = String::new();
        let total_time = self.elapsed();
        
        report.push_str(&format!("Total time: {}\n", format_duration(total_time)));
        
        let mut last_time = self.start_time;
        for (name, time) in &self.checkpoints {
            let checkpoint_duration = time.duration_since(last_time);
            report.push_str(&format!("  {}: {}\n", name, format_duration(checkpoint_duration)));
            last_time = *time;
        }
        
        report
    }
}

impl Default for PerformanceTracker {
    fn default() -> Self {
        Self::new()
    }
}

/// Memory usage tracker
pub struct MemoryTracker {
    peak_usage: u64,
    current_usage: u64,
}

impl MemoryTracker {
    pub fn new() -> Self {
        Self {
            peak_usage: 0,
            current_usage: 0,
        }
    }
    
    pub fn allocate(&mut self, bytes: u64) {
        self.current_usage += bytes;
        if self.current_usage > self.peak_usage {
            self.peak_usage = self.current_usage;
        }
    }
    
    pub fn deallocate(&mut self, bytes: u64) {
        self.current_usage = self.current_usage.saturating_sub(bytes);
    }
    
    pub fn current_usage(&self) -> u64 {
        self.current_usage
    }
    
    pub fn peak_usage(&self) -> u64 {
        self.peak_usage
    }
    
    pub fn current_usage_mb(&self) -> f64 {
        self.current_usage as f64 / 1024.0 / 1024.0
    }
    
    pub fn peak_usage_mb(&self) -> f64 {
        self.peak_usage as f64 / 1024.0 / 1024.0
    }
}

impl Default for MemoryTracker {
    fn default() -> Self {
        Self::new()
    }
}

/// Query complexity analyzer
pub struct QueryAnalyzer;

impl QueryAnalyzer {
    /// Estimate query complexity based on SQL text
    pub fn estimate_complexity(sql: &str) -> QueryComplexity {
        let sql_upper = sql.to_uppercase();
        let mut complexity = QueryComplexity::Simple;
        
        // Check for complex operations
        if sql_upper.contains("JOIN") {
            complexity = QueryComplexity::Medium;
        }
        
        if sql_upper.contains("GROUP BY") || sql_upper.contains("ORDER BY") {
            complexity = std::cmp::max(complexity, QueryComplexity::Medium);
        }
        
        if sql_upper.contains("WINDOW") || sql_upper.contains("OVER") {
            complexity = QueryComplexity::Complex;
        }
        
        // Count subqueries
        let subquery_count = sql.matches('(').count();
        if subquery_count > 2 {
            complexity = QueryComplexity::Complex;
        }
        
        // Check for multiple aggregations
        let agg_functions = ["COUNT", "SUM", "AVG", "MIN", "MAX"];
        let agg_count = agg_functions.iter()
            .map(|func| sql_upper.matches(func).count())
            .sum::<usize>();
        
        if agg_count > 3 {
            complexity = std::cmp::max(complexity, QueryComplexity::Medium);
        }
        
        complexity
    }
    
    /// Estimate memory requirements in bytes
    pub fn estimate_memory_usage(sql: &str, estimated_rows: usize) -> u64 {
        let complexity = Self::estimate_complexity(sql);
        let base_memory_per_row = match complexity {
            QueryComplexity::Simple => 100,   // 100 bytes per row
            QueryComplexity::Medium => 200,   // 200 bytes per row
            QueryComplexity::Complex => 500,  // 500 bytes per row
        };
        
        (estimated_rows * base_memory_per_row) as u64
    }
    
    /// Estimate execution time in milliseconds
    pub fn estimate_execution_time(sql: &str, estimated_rows: usize) -> u64 {
        let complexity = Self::estimate_complexity(sql);
        let base_time_per_thousand_rows = match complexity {
            QueryComplexity::Simple => 1,    // 1ms per 1000 rows
            QueryComplexity::Medium => 5,    // 5ms per 1000 rows
            QueryComplexity::Complex => 20,  // 20ms per 1000 rows
        };
        
        let thousand_rows = (estimated_rows as f64 / 1000.0).ceil() as u64;
        std::cmp::max(1, thousand_rows * base_time_per_thousand_rows)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum QueryComplexity {
    Simple,
    Medium,
    Complex,
}

impl std::fmt::Display for QueryComplexity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            QueryComplexity::Simple => write!(f, "Simple"),
            QueryComplexity::Medium => write!(f, "Medium"),
            QueryComplexity::Complex => write!(f, "Complex"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_format_bytes() {
        assert_eq!(format_bytes(0), "0 B");
        assert_eq!(format_bytes(512), "512.00 B");
        assert_eq!(format_bytes(1024), "1.00 KB");
        assert_eq!(format_bytes(1048576), "1.00 MB");
        assert_eq!(format_bytes(1073741824), "1.00 GB");
    }
    
    #[test]
    fn test_format_duration() {
        assert_eq!(format_duration(Duration::from_millis(500)), "500ms");
        assert_eq!(format_duration(Duration::from_millis(1500)), "1.50s");
        assert_eq!(format_duration(Duration::from_millis(65000)), "1m 5.00s");
    }
    
    #[test]
    fn test_query_complexity() {
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT * FROM table"),
            QueryComplexity::Simple
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT COUNT(*) FROM table GROUP BY column"),
            QueryComplexity::Medium
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT ROW_NUMBER() OVER (ORDER BY id) FROM table"),
            QueryComplexity::Complex
        );
    }
    
    #[test]
    fn test_memory_tracker() {
        let mut tracker = MemoryTracker::new();
        
        tracker.allocate(1024);
        assert_eq!(tracker.current_usage(), 1024);
        assert_eq!(tracker.peak_usage(), 1024);
        
        tracker.allocate(2048);
        assert_eq!(tracker.current_usage(), 3072);
        assert_eq!(tracker.peak_usage(), 3072);
        
        tracker.deallocate(1024);
        assert_eq!(tracker.current_usage(), 2048);
        assert_eq!(tracker.peak_usage(), 3072); // Peak remains
    }
}