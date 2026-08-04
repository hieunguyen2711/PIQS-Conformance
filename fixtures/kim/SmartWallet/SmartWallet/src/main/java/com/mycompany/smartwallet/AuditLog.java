/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.smartwallet;

import java.util.ArrayList;
import java.util.Date;

/**
 *
 * @author kim2
 */
public class AuditLog {
    private ArrayList<String> logs = new ArrayList<>();

    public void logAction(String logEntry) {
        logs.add(new Date().toString() + " - " + logEntry);
    }

    public void showLogs() {
        for (String log : logs) {
            System.out.println(log);
        }
    }    
}
