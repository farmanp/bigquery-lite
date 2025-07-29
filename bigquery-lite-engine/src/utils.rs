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
        let cleaned_sql = Self::remove_comments_and_strings(sql);
        let sql_upper = cleaned_sql.to_uppercase();
        let mut complexity = QueryComplexity::Simple;
        
        // Check for complex operations using word boundaries
        if Self::contains_sql_keyword(&sql_upper, "JOIN") {
            complexity = QueryComplexity::Medium;
        }
        
        if Self::contains_sql_keyword(&sql_upper, "GROUP BY") || Self::contains_sql_keyword(&sql_upper, "ORDER BY") {
            complexity = std::cmp::max(complexity, QueryComplexity::Medium);
        }
        
        if Self::contains_sql_keyword(&sql_upper, "WINDOW") || Self::contains_sql_keyword(&sql_upper, "OVER") {
            complexity = QueryComplexity::Complex;
        }
        
        // Count actual subqueries by looking for SELECT within parentheses
        let subquery_count = Self::count_subqueries(&cleaned_sql);
        if subquery_count > 2 {
            complexity = QueryComplexity::Complex;
        }
        
        // Check for multiple aggregations using word boundaries
        let agg_functions = ["COUNT", "SUM", "AVG", "MIN", "MAX"];
        let agg_count = agg_functions.iter()
            .map(|func| Self::count_sql_function(&sql_upper, func))
            .sum::<usize>();
        
        if agg_count > 3 {
            complexity = std::cmp::max(complexity, QueryComplexity::Medium);
        }
        
        complexity
    }
    
    /// Remove SQL comments and string literals to avoid false positives
    fn remove_comments_and_strings(sql: &str) -> String {
        let mut result = String::new();
        let mut chars = sql.chars().peekable();
        let mut in_single_quote = false;
        let mut in_double_quote = false;
        
        while let Some(ch) = chars.next() {
            match ch {
                '\'' if !in_double_quote => {
                    in_single_quote = !in_single_quote;
                    result.push(' '); // Replace string content with space
                }
                '"' if !in_single_quote => {
                    in_double_quote = !in_double_quote;
                    result.push(' '); // Replace string content with space
                }
                '-' if !in_single_quote && !in_double_quote => {
                    if chars.peek() == Some(&'-') {
                        // Skip line comment
                        chars.next(); // consume second '-'
                        while let Some(ch) = chars.next() {
                            if ch == '\n' {
                                result.push('\n');
                                break;
                            }
                        }
                    } else {
                        result.push(ch);
                    }
                }
                '/' if !in_single_quote && !in_double_quote => {
                    if chars.peek() == Some(&'*') {
                        // Skip block comment
                        chars.next(); // consume '*'
                        let mut found_end = false;
                        while let Some(ch) = chars.next() {
                            if ch == '*' && chars.peek() == Some(&'/') {
                                chars.next(); // consume '/'
                                found_end = true;
                                break;
                            }
                        }
                        if found_end {
                            result.push(' ');
                        }
                    } else {
                        result.push(ch);
                    }
                }
                _ if in_single_quote || in_double_quote => {
                    result.push(' '); // Replace string content with space
                }
                _ => {
                    result.push(ch);
                }
            }
        }
        
        result
    }
    
    /// Check if SQL contains a keyword with proper word boundaries
    fn contains_sql_keyword(sql: &str, keyword: &str) -> bool {
        let pattern = format!(r"\b{}\b", regex::escape(keyword));
        regex::Regex::new(&pattern)
            .map(|re| re.is_match(sql))
            .unwrap_or(false)
    }
    
    /// Count SQL function calls with proper word boundaries
    fn count_sql_function(sql: &str, function_name: &str) -> usize {
        let pattern = format!(r"\b{}\s*\(", regex::escape(function_name));
        regex::Regex::new(&pattern)
            .map(|re| re.find_iter(sql).count())
            .unwrap_or(0)
    }
    
    /// Count actual subqueries by looking for SELECT within parentheses
    fn count_subqueries(sql: &str) -> usize {
        let mut count = 0;
        let mut paren_depth = 0;
        let mut in_subquery = false;
        let sql_upper = sql.to_uppercase();
        let mut i = 0;
        let chars: Vec<char> = sql_upper.chars().collect();
        
        while i < chars.len() {
            match chars[i] {
                '(' => {
                    paren_depth += 1;
                    in_subquery = false;
                }
                ')' => {
                    paren_depth -= 1;
                    in_subquery = false;
                }
                'S' if paren_depth > 0 && !in_subquery => {
                    // Check if this starts "SELECT"
                    if i + 6 <= chars.len() {
                        let word: String = chars[i..i+6].iter().collect();
                        if word == "SELECT" {
                            // Check if it's a word boundary before and after
                            let before_ok = i == 0 || !chars[i-1].is_alphanumeric();
                            let after_ok = i + 6 >= chars.len() || !chars[i+6].is_alphanumeric();
                            if before_ok && after_ok {
                                count += 1;
                                in_subquery = true;
                            }
                        }
                    }
                }
                _ => {}
            }
            i += 1;
        }
        
        count
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
    fn test_query_complexity_false_positives() {
        // Test that keywords in comments don't affect complexity
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT * FROM table -- This has JOIN in comment"),
            QueryComplexity::Simple
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT * FROM table /* Contains GROUP BY in block comment */"),
            QueryComplexity::Simple
        );
        
        // Test that keywords in string literals don't affect complexity
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT 'This has JOIN keyword' FROM table"),
            QueryComplexity::Simple
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT \"Contains GROUP BY\" FROM table"),
            QueryComplexity::Simple
        );
        
        // Test actual JOIN vs false positives
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT * FROM table1 JOIN table2 ON table1.id = table2.id"),
            QueryComplexity::Medium
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT 'JOINING' FROM table"),
            QueryComplexity::Simple
        );
        
        // Test subquery counting accuracy
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT * FROM (SELECT * FROM table1) t1"),
            QueryComplexity::Simple // Only one subquery
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT * FROM table WHERE col IN (1, 2, 3)"),
            QueryComplexity::Simple // Parentheses without SELECT
        );
        
        // Test function counting accuracy
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT COUNT(*) FROM table"),
            QueryComplexity::Simple // Only one aggregation
        );
        
        assert_eq!(
            QueryAnalyzer::estimate_complexity("SELECT 'COUNT is important' FROM table"),
            QueryComplexity::Simple // COUNT in string literal
        );
    }
    
    #[test]
    fn test_remove_comments_and_strings() {
        // Test line comments
        let sql = "SELECT * FROM table -- This is a comment with JOIN";
        let cleaned = QueryAnalyzer::remove_comments_and_strings(sql);
        assert!(!cleaned.contains("JOIN"));
        assert!(cleaned.contains("SELECT"));
        
        // Test block comments
        let sql = "SELECT * /* comment with GROUP BY */ FROM table";
        let cleaned = QueryAnalyzer::remove_comments_and_strings(sql);
        assert!(!cleaned.contains("GROUP BY"));
        assert!(cleaned.contains("SELECT"));
        
        // Test string literals
        let sql = "SELECT 'text with JOIN keyword' FROM table";
        let cleaned = QueryAnalyzer::remove_comments_and_strings(sql);
        assert!(!cleaned.contains("JOIN"));
        assert!(cleaned.contains("SELECT"));
        
        // Test mixed quotes
        let sql = r#"SELECT 'single quote' AND "double quote with GROUP BY" FROM table"#;
        let cleaned = QueryAnalyzer::remove_comments_and_strings(sql);
        assert!(!cleaned.contains("GROUP BY"));
        assert!(cleaned.contains("SELECT"));
    }
    
    #[test]
    fn test_sql_keyword_detection() {
        // Test proper word boundaries
        assert!(QueryAnalyzer::contains_sql_keyword("SELECT * FROM table JOIN other", "JOIN"));
        assert!(!QueryAnalyzer::contains_sql_keyword("SELECT * FROM tableJOINother", "JOIN"));
        assert!(!QueryAnalyzer::contains_sql_keyword("SELECT * FROM JOINtable", "JOIN"));
        assert!(!QueryAnalyzer::contains_sql_keyword("SELECT * FROM tableJOIN", "JOIN"));
        
        // Test multi-word keywords
        assert!(QueryAnalyzer::contains_sql_keyword("SELECT * FROM table GROUP BY col", "GROUP BY"));
        assert!(!QueryAnalyzer::contains_sql_keyword("SELECT * FROM tableGROUP BYcol", "GROUP BY"));
    }
    
    #[test]
    fn test_function_counting() {
        // Test proper function detection
        assert_eq!(QueryAnalyzer::count_sql_function("SELECT COUNT(*) FROM table", "COUNT"), 1);
        assert_eq!(QueryAnalyzer::count_sql_function("SELECT COUNT(*), SUM(col) FROM table", "COUNT"), 1);
        assert_eq!(QueryAnalyzer::count_sql_function("SELECT COUNT(*), SUM(col) FROM table", "SUM"), 1);
        
        // Test false positives
        assert_eq!(QueryAnalyzer::count_sql_function("SELECT COUNTER FROM table", "COUNT"), 0);
        assert_eq!(QueryAnalyzer::count_sql_function("SELECT COUNT_TOTAL FROM table", "COUNT"), 0);
    }
    
    #[test]
    fn test_subquery_counting() {
        // Test actual subqueries
        assert_eq!(QueryAnalyzer::count_subqueries("SELECT * FROM (SELECT * FROM table) t"), 1);
        assert_eq!(QueryAnalyzer::count_subqueries("SELECT * FROM (SELECT * FROM (SELECT * FROM table) t1) t2"), 2);
        
        // Test non-subquery parentheses
        assert_eq!(QueryAnalyzer::count_subqueries("SELECT * FROM table WHERE col IN (1, 2, 3)"), 0);
        assert_eq!(QueryAnalyzer::count_subqueries("SELECT COUNT(*) FROM table"), 0);
        
        // Test mixed cases
        assert_eq!(QueryAnalyzer::count_subqueries("SELECT * FROM (SELECT * FROM table) t WHERE col IN (1, 2, 3)"), 1);
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