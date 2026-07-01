use pyo3::prelude::*;
use std::collections::HashMap;

const HEAT_CRUSH: f64 = 0.7;

#[pyclass]
struct NexusCore {
    scores: HashMap<String, f64>,
}

#[pymethods]
impl NexusCore {
    #[new]
    fn new() -> Self {
        Self {
            scores: HashMap::new(),
        }
    }

    /// Aggregate 10-axis scores → heat (0..1). Auto-crush when heat ≥ 0.7.
    fn score(&mut self, ip: String, axes: Vec<f64>) -> f64 {
        let n = axes.len().max(1) as f64;
        let heat: f64 = axes.iter().sum::<f64>() / (n * 10.0);
        let _ = blake3::hash(ip.as_bytes());
        self.scores.insert(ip, heat);
        heat
    }

    fn heat_crush_ips(&self, threshold: Option<f64>) -> Vec<String> {
        let t = threshold.unwrap_or(HEAT_CRUSH);
        self.scores
            .iter()
            .filter(|(_, h)| **h >= t)
            .map(|(ip, _)| ip.clone())
            .collect()
    }
}

#[pymodule]
fn nexus_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NexusCore>()?;
    Ok(())
}
