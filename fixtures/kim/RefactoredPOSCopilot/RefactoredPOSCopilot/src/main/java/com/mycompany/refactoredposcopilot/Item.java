/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

/**
 *
 * @author kim2
 */
// Item class remains the same
class Item {
    private int ID;
    private String name;
    private double price;

    public Item(int ID, String name, double price) {
        this.ID = ID;
        this.name = name;
        this.price = price;
    }

    public String getName() { return name; }
    public double getPrice() { return price; }
    public int getID() { return ID; }
}
