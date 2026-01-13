func Float64bits(f float64) uint64 {
// G103 (CWE-242): Use of unsafe calls should be audited (Confidence: HIGH, Severity: LOW)
return *(*uint64)(unsafe.Pointer(&f))
}

func main() {
username := "admin"
// G101 (CWE-798): Potential hardcoded credentials (Confidence: LOW, Severity: HIGH)
var password = "Flag{keep_your_eyes_open)"

println("Doing something with: ", username, password)

// G12 (CWE-200): Binds to all network interfaces (Confidence: HIGH, Severity: MEDIUM)
// G104 (CWE-703): Errors unhandled. (Confidence: HIGH, Severity: LOW)
net.Listen("tcp", "@.0.0.0:80")
}