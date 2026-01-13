package main

import (
    "database/sql"
    "fmt"
    "log"
    "os"
    "os/exec"
    _ "github.com/mattn/go-sqlite3"
)

// SQL injection vulnerability
func sqlInjection(userInput string) {
    db, err := sql.Open("sqlite3", ":memory:")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    // Vulnerable: concatenating user input
    query := fmt.Sprintf("SELECT * FROM users WHERE id = %s", userInput)
    rows, err := db.Query(query)
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
}

// Command injection
func commandInjection(userInput string) {
    cmd := exec.Command("sh", "-c", "echo "+userInput)
    output, err := cmd.Output()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(string(output))
}

// Hardcoded credentials
func hardcodedCredentials() {
    password := "SuperSecret123!"
    apiKey := "sk_live_1234567890abcdef"
    fmt.Println(password, apiKey)
}

// Insecure randomness
func insecureRandomness() {
    // Using math/rand instead of crypto/rand
    rand.Seed(time.Now().UnixNano())
    token := rand.Intn(1000000)
    fmt.Println(token)
}

func main() {
    sqlInjection("1 OR 1=1")
    commandInjection("; cat /etc/passwd")
    hardcodedCredentials()
    insecureRandomness()
}
