/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsgemini;

/**
 *
 * @author kim2
 */
// Example of an AuditLogObserver (for demonstration)
class ConsoleLogger implements AuditLogObserver {
    @Override
    public void onLogEvent(String logEntry) {
        System.out.println("Log Event: " + logEntry);
    }
}
